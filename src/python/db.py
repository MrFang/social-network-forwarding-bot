from dotenv import dotenv_values
import psycopg2
import psycopg2.extras

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


def get_all_connections(bot, user_id):
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
            channel_name = get_channel_name_by_id(bot, link['channel_id'])
            message += f"{num+1}) " \
                f"{channel_name} \n"
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
        ''', (channel_id, chat_id))


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


def get_channel_name_by_id(bot, channel_id):
    channel = bot.get_chat(channel_id)
    return channel.title


def channel_is_exist(channel_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
        SELECT * from channel_to_vk WHERE channel_id = %s
        ''', (channel_id, )
                    )
        data = cur.fetchone()
        cur.close()
    if data:
        return True
    else:
        return False


def get_deferred_posts(channel_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute('''
            SELECT id, post_text
            FROM deferred_posts
            WHERE channel_id = %s
        ''', (channel_id,))

        posts = cur.fetchall()
        ids = [post['id'] for post in posts]

        if len(ids) > 0:
            cur.execute('''
                DELETE FROM deferred_posts
                WHERE id IN (%s)
            ''', (', '.join(ids),))

    return [post['post_text'] for post in posts]


def defer_post(from_channel, text):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            INSERT INTO deferred_posts
            (channel_id, post_text) VALUES
            (%s, %s)
        ''', (from_channel, text))


def get_telegram_user_by_channel_id(channel_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute('''
            SELECT issued_by
            FROM channel_to_vk
            WHERE channel_id = %s
        ''', (channel_id,))

        user_id = cur.fetchone()['issued_by']

    return user_id


def add_pending_login(chat_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cur.execute('''
                INSERT INTO pending_logins
                (user_id) VALUES
                (%s)
            ''', (chat_id,))
        except psycopg2.IntegrityError:
            pass


def is_pending_login(chat_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute('''
            SELECT id
            FROM pending_logins
            WHERE user_id = %s
        ''', (chat_id, ))

        return len(cur.fetchall()) > 0


def delete_pending_login(chat_id):
    with connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute('''
            DELETE FROM pending_logins
            WHERE user_id = %s
        ''', (chat_id, ))
