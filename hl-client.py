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

load_dotenv()
token = os.environ.get('BOT_TOKEN')
period = int(os.environ.get('BOT_PERIOD', default='180'))  # in seconds

state_storage = StateMemoryStorage()  # replace with Redis?
bot = telebot.TeleBot(token, state_storage=state_storage)

class MyStates(StatesGroup):
    server = State()
    port = State()

class ServerData:
    last_check_time: datetime = None
    connection_info = None
    last_state = None
    last_state_message: str = None
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
    server = None

settings_per_user = {}

def get_settings(message) -> UserSettings:
    user_settings = settings_per_user.get(message.chat.id)
    if user_settings is None:
        user_settings = UserSettings(message.chat.id)
        settings_per_user[message.chat.id] = user_settings

    return user_settings

server_states = {}

def get_server_state(connection_info) -> ServerData:
    state = server_states.get(connection_info)
    if state is None:
        state = ServerData(connection_info)
        server_states[connection_info] = state
    
    return state


def check_hldm(serverData: ServerData):
    serverData.last_check_time = datetime.datetime.now()
    server, _ = serverData.connection_info
    try:
        state = a2s.info(serverData.connection_info)
        serverData.last_state = state        
        serverData.alive = True
        serverData.last_state_message = "Server {} [{}] has {} players".format(server, state.map_name, state.player_count)
        serverData.last_check_passed_time = datetime.datetime.now()
    except Exception as err:
        serverData.alive = False
        serverData.last_state_message = "Server {} check failed. Last time seen {}".format(server, serverData.last_check_passed_time)
        print(err)
        return False
    
    return True
    

def send_hldm_state_for_user(message):
    user_settings = get_settings(message)
    if user_settings and user_settings.server:
        server_data = user_settings.server

        prev_state = server_data.last_state_message
        check_hldm(server_data)
        if prev_state != server_data.last_state_message and prev_state is not None:
            sendNewServerStateForSubscribers(server_data)
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
        send_hldm_state_for_user(message)
    else:
        bot.send_message(message.chat.id, "HalfLife DM state checking bot")

def register_server(message):
    parts = message.text.split()[1:]
    if len(parts) == 2:
        try:
            user_settings = get_settings(message)
            connection_info = (parts[0], int(parts[1]))
            serverState = get_server_state(connection_info)            
            user_settings.server = serverState

            bot.delete_state(message.chat.id, message.chat.id)
            send_hldm_state_for_user(message)
        except:
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
    bot.send_message(message.chat.id, 'Port? [default=27015]')

@bot.message_handler(state=MyStates.port, is_digit=True)
def get_port(message):
    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['port'] = int(message.text)
            
            user_settings = get_settings(message)
            connection_info = (data['server'], data['port'])
            serverState = get_server_state(connection_info)            
            user_settings.server = serverState

        bot.delete_state(message.chat.id, message.chat.id)
        send_hldm_state_for_user(message)
    except Exception:
        bot.send_message(message.chat.id, 'Wrong port, try again')

# Any state
@bot.message_handler(state="*", commands=['cancel'])
def any_state(message):
    bot.send_message(message.chat.id, "Your state was cancelled.")
    bot.delete_state(message.chat.id, message.chat.id)

def checkAvailableServers():
    print('Check Servers cycle')
    for server_data in server_states.values():
        checkServersState(server_data)

def checkServersState(server_data: ServerData):
    try:
        print('Check state {}'.format(server_data.connection_info))
        prev_state = server_data.last_state_message
        check_hldm(server_data)
        if prev_state != server_data.last_state_message:
            sendNewServerStateForSubscribers(server_data)
    except Exception as err:
        print(err)

def sendNewServerStateForSubscribers(server_data: ServerData):
    for chat_id, chat_settings in settings_per_user.items():
        if chat_settings.server is server_data:
            bot.send_message(
                chat_id,
                server_data.last_state_message
            )

async def serverStateCycle():
    while True:
        checkAvailableServers()
        await asyncio.sleep(period)

def startScheduler():
    print('Scheduler')
    serverStateThread = threading.Thread(target=asyncio.run, args=(serverStateCycle(),))
    serverStateThread.start()

def startBotProcessing():
    print('Bot messages processor')
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.add_custom_filter(custom_filters.IsDigitFilter())
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    startScheduler()
    startBotProcessing()
