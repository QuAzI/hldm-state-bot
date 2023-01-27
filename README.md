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

## Development prerequisites

```
python -m virtualenv .venv
.venv/Scripts/activate
pip install -r .\requirements.txt
```
