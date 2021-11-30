import psycopg2
import telebot
import argparse
import requests
import vk
from dotenv import dotenv_values
import os

from telebot import types

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


database = []


@bot.message_handler(commands=['start', 'menu'])
def main(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    register_key = types.KeyboardButton("Register new link")
    delete_key = types.KeyboardButton("Delete existing link")
    list_key = types.KeyboardButton("List of your links")
    keyboard.add(register_key)
    keyboard.add(delete_key)
    keyboard.add(list_key)
    bot.send_message(message.chat.id, "Choose action", reply_markup=keyboard)


@bot.message_handler(content_types=['text'])
def text_parse(message):
    if message.text == "Register new link":
        new_link(message)
    elif message.text == "List of your links":
        if not database:
            bot.send_message(message.chat.id, "No links")
        else:
            list_message = "Your active links are: \n"
            for num, link in enumerate(database):
                new_line = f"{num+1}) {link['tg_channel_name']} - {link['vk_link']} \n"
                list_message = list_message + new_line
                #list_message = list_message + link['tg_channel_name'] + ' - ' +  link['vk_link'] + "\n"
            bot.send_message(message.chat.id, list_message)
    elif message.text == "Delete existing link":
        delete_link(message)


def new_link(message):
    message_one = "Please, show me title of the channel you want to repost"
    bot.send_message(message.chat.id, message_one)
    bot.register_next_step_handler(message, get_channel_name)


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


def get_channel_name(message):
    database.append(dict())
    database[-1]['tg_channel_name'] = message.text
    bot.send_message(message.chat.id, "Please, show me vk link")
    bot.register_next_step_handler(message, get_vk_link)


def get_vk_link(message):
    database[-1]['vk_link'] = message.text
    print(database)
    complete_message = "Your link successfully added!! \n Choose your action"
    bot.send_message(message.chat.id, complete_message)


def delete_link(message):
    message_one = "Please, show me number of the channel you want to delete"
    bot.send_message(message.chat.id, message_one)
    bot.register_next_step_handler(message, delete_current_link)


def delete_current_link(message):
    if int(message.text) <= len(database):
        del database[int(message.text) - 1]
        bot.send_message(message.chat.id, "Successfully deleted \n Choose your action")
    else:
        bot.send_message(message.chat.id, "You was wrong in your number. Please, try again")


bot.infinity_polling()


