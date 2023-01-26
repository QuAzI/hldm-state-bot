#  HalfLife DM state checking bot

Bot will check HalfLife DeathMatch server state each 5 minutes

## Commands

`/reg hostname port` to setup server data
`/state` to get state right now

## Token

Should be present in env. You can write it in `.env` file
```
BOT_TOKEN = 'AVAKADAKADABRA'
```

or pass as container arguments
```
docker build -t hldm-state-bot .
docker run --name hldm-state-bot -e BOT_TOKEN='AVAKADAKADABRA' -d hldm-state-bot:latest
```
