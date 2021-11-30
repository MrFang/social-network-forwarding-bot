# Social Network Forwarding bot
1. Create file `.env` and set variables:
`SNF_BOT_DB_PASS`, `SNF_BOT_TELEGRAM_TOKEN`, `SNF_BOT_VK_TOKEN` and `SNF_BOT_DB_HOST`.
See example in `.env.example`

### With docker
2. Start docker containers: `docker-compose up -d`

### Without docker
2. Setup PostgreSQL
3. Install python dependencies: `pip install -r requirements.txt`
4. Run app: `python3 src/python/app.py`

In any case Init db with `src/sql/schema.sql`