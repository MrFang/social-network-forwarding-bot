## With Docker
1. Create file `.env` and set variables `SNF_BOT_DB_PASS` and `SNF_BOT_TELEGRAM_TOKEN`.
See example in `.env.example`
2. Start docker containers: `docker-compose up -d`

## Without Docker 
1. Setup PostgreSQL. Bot will connect to database `postgres` as user `postgres`
2. Start bot with command:
    `python3 src/python/app.py
    --pg-host <host>
    --pg-password <password>
    --tg-token <token>`.
    Where `host` is your address to your postgres, `password` is password to your postgres, `token` is token to your telegram bot