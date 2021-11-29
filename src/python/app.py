import psycopg2
import telebot
import argparse
import requests
import vk

parser = argparse.ArgumentParser(description='Hello DB web application')
parser.add_argument(
    '--pg-host', help='PostgreSQL host name', default='localhost')
parser.add_argument('--pg-port', help='PostgreSQL port', default=5432)
parser.add_argument('--pg-user', help='PostgreSQL user', default='postgres')
parser.add_argument('--pg-password', help='PostgreSQL password', default='')
parser.add_argument(
    '--pg-database', help='PostgreSQL database', default='postgres')
parser.add_argument('--tg-token', help='Telegram bot token', default='')

args = parser.parse_args()

connection = psycopg2.connect(
    database=args.pg_database,
    user=args.pg_user,
    host=args.pg_host,
    password=args.pg_password
)

bot = telebot.TeleBot(args.tg_token, parse_mode=None)
vk_token = 'e0bbc661300067cbac41606ea905c2f49aa7db5d5e0e14f34fa31207283c96e38314d9dc59f2e07b17341'
app_id = 8013095


def init_session():
    session = vk.Session(access_token=vk_token)
    vk_api = vk.API(session,  v='5.131')
    return vk_api


@bot.message_handler(func=lambda m: True)
def echo_all(message):
    # bot.reply_to(message, message.text)
    vk_api = init_session()
    vk_api.wall.post(message=message.text)


@bot.message_handler(content_types=["photo"])
def echo_all(message):
    file_id = message.photo[-1].file_id
    file_path = bot.get_file(file_id)
    download_link = f'https://api.telegram.org/file/bot{args.tg_token}/{file_path}'

    requests.get(download_link)
    vk_api = init_session()
    vk_photo_server = vk_api.photos.getWallUploadServer()
    upload_url = vk_photo_server['upload_url']
    resp = requests.post(upload_url, files={'file': open(file_path, 'rb')}).json()
    photo = vk_api.photos.saveWallPhoto(server=resp['server'], photo=resp['photo'], hash=resp['hash'])
    bot.file_path
    bot.reply_to(message, file_path)
    # link = f'https://api.telegram.org/file/bot{args.tg_token}/{path}'
    # bot.send_photo(message.chat.id, file_id, caption=message.caption)
    # requests.post(f'https://api.vk.com/method/wall.post?v=5.131?owner_id=89685577&message={message.caption}&attachments=photo{}&access_token={access_token}')


bot.infinity_polling()
