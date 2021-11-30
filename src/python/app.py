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
tg_token = config['SNF_BOT_TELEGRAM_TOKEN']
bot = telebot.TeleBot(tg_token, parse_mode=None)
vk_token = config['SNF_BOT_VK_TOKEN']  # TODO: move to DB


def init_session():
    session = vk.Session(access_token=vk_token)
    vk_api = vk.API(session,  v='5.131')
    return vk_api


@bot.message_handler(func=lambda m: True)
def echo_all(message):
    vk_api = init_session()
    vk_api.wall.post(message=message.text)


@bot.message_handler(content_types=["photo"])
def echo_all(message):
    file_id = message.photo[-1].file_id
    file_path = bot.get_file(file_id).file_path
    download_link = f'https://api.telegram.org/file/bot{tg_token}/{file_path}'

    filename = download_link.split('/')[-1]
    download_response = requests.get(download_link,  allow_redirects=True)

    vk_api = init_session()
    vk_photo_server = vk_api.photos.getWallUploadServer()
    upload_url = vk_photo_server['upload_url']
    open(filename, 'wb').write(download_response.content)
    img = {'photo': (filename, open(filename, 'rb'))}

    resp = requests.post(upload_url, files=img).json()
    photo_id = vk_api.photos.saveWallPhoto(server=resp['server'], photo=resp['photo'], hash=resp['hash'])

    photo_id = photo_id[0]
    photo_id = 'photo' + str(photo_id['owner_id']) + '_' + str(photo_id['id'])

    vk_api.wall.post(attachments=photo_id, message=message.caption)


bot.infinity_polling()
