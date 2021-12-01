from dotenv import dotenv_values
import psycopg2

config = dotenv_values('.env')

try:
    connection = psycopg2.connect(
        database='postgres',
        user='postgres',
        host=config['SNF_BOT_DB_HOST'],
        password=config['SNF_BOT_DB_PASS']
    )
    print("Connection successful")
except Exception:
    print("Error during open DB")
    raise Exception


def get_all_connections(cur, user_id):
    cur.execute("SELECT * FROM channel_to_vk WHERE issued_by = %s",
                (user_id, )
                )
    data = cur.fetchall()
    message = "Your active links are: \n"
    if len(data) == 0:
        return False
    for num, link in enumerate(data):
        message += f"{num+1}) " \
            "{link['channel_id']} - {link['vk_access_token']}\n"
    return message
