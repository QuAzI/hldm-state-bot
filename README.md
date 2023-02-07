# Death Match state checking bot

Bot checks game server state each 3 minutes and reports if something changed: how many players play, which map, server unavailable.

Based on [python-a2s](https://github.com/Yepoleb/python-a2s) and should support Valve Source and GoldSource servers:
- Half-Life (that's for what I developed bot and tested)
- Half-Life 2
- Team Fortress 2
- Counter-Strike 1.6
- Counter-Strike: Global Offensive
- ARK: Survival Evolved
- Rust


## Commands

`/reg hostname port` to set up server data

`/state` to get state right now


## Settings

### Token

Token should be present in env. You can write it in `.env` file
```
BOT_TOKEN = 'AVAKADAKADABRA'
```

or pass as container arguments
```
docker build -t hldm-state-bot .
docker run --name hldm-state-bot -e BOT_TOKEN='AVAKADAKADABRA' -d hldm-state-bot:latest
```

Please ensure that only one bot work with the same token at one time!

### Time between server state checks

By the same way define `BOT_PERIOD`. By default 42 seconds


## Development prerequisites

```
python -m virtualenv .venv
.venv/Scripts/activate
pip install -r .\requirements.txt
```


## Deployment

Clone repo into some server directory, as example into `~/docker-server/hldm-state-bot`

Create docker-compose.yml
```yaml
version: '3.9'

services:
  hldm-state-bot:
    container_name: hldm-state-bot
    hostname: hldm-state-bot
    build:
      context: .
      dockerfile: Dockerfile

    volumes:
      - data:/app/data
    environment:
      - BOT_TOKEN=AVAKADAKADABRA
      - BOT_PERIOD=30
    restart: on-failure:7

volumes:
  data:

networks:
  default:
    external:
      name: network
```

Create `.git/hooks/post-merge`

```bash
#!/bin/sh

docker-compose up -d --build
```

And make it executable. Now you can run `git pull` to deploy from master


Or you can automate with crontab.

Run `crontab -e` and write schedule

```bash
*/15 * * * * git -C ~/docker-server/hldm-state-bot pull
```
