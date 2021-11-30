import psycopg2
import telebot
import argparse
import requests
import vk
from dotenv import dotenv_values
import os

if not os.path.isfile('.env'):
    raise RuntimeError('.env file does not exist')

config = dotenv_values('.env')

connection = psycopg2.connect(
    database='postgres',
    user='postgres',
    host=config['SNF_BOT_DB_HOST'],
    password=config['SNF_BOT_DB_PASS']
)

bot = telebot.TeleBot(config['SNF_BOT_TELEGRAM_TOKEN'], parse_mode=None)
vk_token = config['SNF_BOT_VK_TOKEN']  # TODO: move to DB

def init_session():
    session = vk.Session(access_token=vk_token)
    vk_api = vk.API(session,  v='5.131')
    return vk_api


@bot.message_handler(func=lambda m: True)
def echo_all(message)
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
