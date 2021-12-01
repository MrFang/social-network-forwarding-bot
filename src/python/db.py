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


def get_all_connections(user_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM channel_to_vk WHERE issued_by = %s",
                    (user_id, )
                    )
        data = cur.fetchall()
        message = "Your active links are: \n"
        if len(data) == 0:
            return False
        for num, link in enumerate(data):
            message += f"{num+1}) " \
                f"{link['channel_id']} - {link['vk_access_token']}\n"
    return message


def data_count(user_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM channel_to_vk WHERE issued_by = %s",
                    (user_id,)
                    )
        data = cur.fetchall()
        cur.close()
    return len(data)

def add_new_record(channel_id, chat_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            INSERT INTO channel_to_vk
            (channel_id, issued_by) VALUES
            (%s, %s)
        ''', (channel_id, chat_id)
                    )


def save_access_token(channel_id, access_token, chat_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            SELECT id
            FROM channel_to_vk
            WHERE channel_id = %s
                AND issued_by = %s
                AND vk_access_token IS NULL
            ORDER BY issued_at DESC
            LIMIT 1
        ''', (channel_id, chat_id))
        record_id = cur.fetchone()['id']

        cur.execute('''
            UPDATE channel_to_vk
            SET vk_access_token = %s
            WHERE id = %s
        ''', (access_token, record_id))


def delete_line(user_id, num):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM channel_to_vk WHERE issued_by = %s",
                    (user_id,)
                    )
        data = cur.fetchall()
        del_id = data[num-1]['id']
        cur.execute("DELETE FROM channel_to_vk WHERE id = %s",
                    (del_id, )
                    )


def get_vk_auth_token(channel_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            SELECT vk_access_token
            FROM channel_to_vk
            WHERE channel_id = %s
        ''', (channel_id,))
        token = cur.fetchone()['vk_access_token']
    return token
