from dotenv import load_dotenv
import os
import telebot
from telebot import custom_filters
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
import a2s
import threading
import asyncio
import datetime
import json

class MyStates(StatesGroup):
    server = State()
    port = State()

class ServerData:
    last_check_time: datetime = None
    connection_info = None
    last_state = None
    last_state_message: str | None = None
    last_check_passed_time: datetime = None
    alive: bool = False

    def __init__(self, connection_info):
        self.connection_info = connection_info
        self.last_check_time = None
        self.last_state = None
        self.last_state_message = None
        self.last_check_passed_time = None
        self.alive = False

class UserSettings:
  chat_id: str = None
  server: ServerData = None

  def __init__(self, chat_id):
    self.chat_id = chat_id


load_dotenv()
token = os.environ.get('BOT_TOKEN')
period = int(os.environ.get('BOT_PERIOD', default='42'))  # in seconds

state_storage = StateMemoryStorage()  # replace with Redis?
bot = telebot.TeleBot(token, state_storage=state_storage)

settings_per_user = {}
server_states = {}


def get_settings(message) -> UserSettings:
    user_settings = settings_per_user.get(message.chat.id)
    if user_settings is None:
        user_settings = UserSettings(message.chat.id)
        settings_per_user[message.chat.id] = user_settings

    return user_settings

def get_server_state(connection_info) -> ServerData:
    state = server_states.get(connection_info)
    if state is None:
        state = ServerData(connection_info)
        server_states[connection_info] = state
    
    return state


def check_server_state(server_data: ServerData):
    server_data.last_check_time = datetime.datetime.now()
    server, _ = server_data.connection_info
    retry_num = 0
    while retry_num < 3:
        retry_num += 1
        print('Check state: {} iter {}'.format(server_data.connection_info, retry_num))
        try:
            state = a2s.info(server_data.connection_info, timeout=15)
            server_data.last_state = state
            server_data.alive = True
            server_data.last_state_message = "Server {} [{} on '{}'] has {} players".format(server, state.game, state.map_name, state.player_count)
            server_data.last_check_passed_time = datetime.datetime.now()
            return True
        except Exception as err:
            server_data.alive = False
            server_data.last_state_message = "Server {} check failed. Last time seen {}".format(server, server_data.last_check_passed_time)
            print(err)
        finally:
            print(server_data.last_state_message)

    return False

def reply_server_state_for_user(message):
    user_settings = get_settings(message)
    if user_settings and user_settings.server:
        server_data = user_settings.server

        prev_state = server_data.last_state_message
        check_server_state(server_data)
        if prev_state != server_data.last_state_message and prev_state is not None:
            send_new_server_state_for_subscribers(server_data)
        else:
           bot.send_message(
               message.chat.id,
               user_settings.server.last_state_message
           )
    else:
        bot.send_message(message.chat.id, "Use `/reg hostname port` to register server")

@bot.message_handler(commands=['start', 'reg', 'state'])
def start(message):
    if message.text.startswith('/reg'):
        register_server(message)
    elif message.text.startswith("/state"):
        reply_server_state_for_user(message)
    else:
        bot.send_message(
            message.chat.id, 
            "Game state checking bot. To check Source and GoldSource servers (Half-Life, Half-Life 2, Team Fortress 2, Counter-Strike 1.6, Counter-Strike: Global Offensive, ARK: Survival Evolved, Rust)"
        )

def load_settings():
    global settings_per_user
    try:
        if os.path.exists('data/user_data.json'):
            with open('data/user_data.json', 'r') as f:
                settings_per_user = json.load(f)
    except Exception as err:
        print(err)

def save_settings():
    try:
        json_data = json.dumps(settings_per_user)

        if not os.path.exists('data'):
            os.makedirs('data')

        with open('data/user_data.json', 'w') as f:
            f.write(json_data)
    except Exception as err:
        print(err)

def register_server(message):
    parts = message.text.split()[1:]
    if len(parts) == 2:
        try:
            user_settings = get_settings(message)
            connection_info = (parts[0], int(parts[1]))
            server_state = get_server_state(connection_info)
            user_settings.server = server_state

            bot.delete_state(message.chat.id, message.chat.id)
            reply_server_state_for_user(message)

            save_settings()
        except Exception as err:
            print(err)
            bot.send_message(message.chat.id, "Please check settings")
    elif message.chat.type == "private":
        bot.set_state(message.from_user.id, MyStates.server, message.chat.id)
        bot.send_message(message.chat.id, "Which hostname you want to monitor?")
    else:
        bot.send_message(message.chat.id, "Use `/reg hostname port` to register server")

@bot.message_handler(state=MyStates.server)
def get_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        # TODO validate
        data['server'] = message.text

    bot.set_state(message.from_user.id, MyStates.port, message.chat.id)    
    bot.send_message(message.chat.id, 'Port? [default=27015 for HL]')

@bot.message_handler(state=MyStates.port, is_digit=True)
def get_port(message):
    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['port'] = int(message.text)
            
            user_settings = get_settings(message)
            connection_info = (data['server'], data['port'])
            server_state = get_server_state(connection_info)
            user_settings.server = server_state

        bot.delete_state(message.chat.id, message.chat.id)
        reply_server_state_for_user(message)
    except Exception as err:
        print(err)
        bot.send_message(message.chat.id, 'Wrong port, try again')

# Any state
@bot.message_handler(state="*", commands=['cancel'])
def any_state(message):
    bot.send_message(message.chat.id, "Your state was cancelled.")
    bot.delete_state(message.chat.id, message.chat.id)

def check_available_servers():
    print('Check Servers cycle: {} servers'.format(len(server_states)))
    for server_data in server_states.values():
        check_server_state_and_notify(server_data)

def check_server_state_and_notify(server_data: ServerData):
    try:
        print('Check state {}'.format(server_data.connection_info))
        prev_state = server_data.last_state_message
        check_server_state(server_data)
        if prev_state != server_data.last_state_message:
            send_new_server_state_for_subscribers(server_data)
    except Exception as err:
        print(err)

def send_new_server_state_for_subscribers(server_data: ServerData):
    print('Send state {} {}'.format(server_data.connection_info, server_data.last_state_message))
    for chat_id, chat_settings in settings_per_user.items():
        if chat_settings.server is server_data:
            bot.send_message(
                chat_id,
                server_data.last_state_message
            )

async def server_state_cycle():
    while True:
        check_available_servers()
        await asyncio.sleep(period)

def start_server_state_scheduler():
    print('Scheduler')
    server_state_thread = threading.Thread(target=asyncio.run, args=(server_state_cycle(),))
    server_state_thread.start()

def start_bot_processing():
    print('Bot messages processor')
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.add_custom_filter(custom_filters.IsDigitFilter())
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    load_settings()
    start_server_state_scheduler()
    start_bot_processing()
