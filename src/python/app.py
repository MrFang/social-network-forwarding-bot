import psycopg2
import psycopg2.extras
import telebot
import db_funcs
import requests
import vk
from dotenv import dotenv_values
import os
import time

from telebot import types

if not os.path.isfile('.env'):
    raise RuntimeError('.env file does not exist')

config = dotenv_values('.env')

try:
    connection = psycopg2.connect(
        database='postgres',
        user='postgres',
        host=config['SNF_BOT_DB_HOST'],
        password=config['SNF_BOT_DB_PASS']
    )
    print("Connection successful")
    succesfull_connect = True
except:
    print("Error during open DB")
    raise Exception



tg_token = config['SNF_BOT_TELEGRAM_TOKEN']
bot = telebot.TeleBot(tg_token, parse_mode=None)
vk_token = config['SNF_BOT_VK_TOKEN']  # TODO: move to DB
vk_token_wrong = 'e0bb9661300067cbac41606ea905c2f49aa7db5d5e0e14f34fa31207283c96e38314d9dc59f2e07b17341'

def init_session():
    session = vk.Session(access_token=vk_token_wrong)
    vk_api = vk.API(session,  v='5.131')
    return vk_api




database = dict()
del_keyboard = telebot.types.ReplyKeyboardRemove()
keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

@bot.message_handler(commands=['start', 'menu'])
def main(message):
    register_key = types.KeyboardButton("🖇 Register new link")
    delete_key = types.KeyboardButton("✂️ Delete existing link")
    list_key = types.KeyboardButton("📝 List of your links")
    keyboard.add(register_key)
    keyboard.add(delete_key)
    keyboard.add(list_key)
    bot.send_message(message.chat.id, "Choose action", reply_markup=keyboard)


@bot.message_handler(content_types=['text'])
def text_parse(message):
    if message.text == "🖇 Register new link":
        global database
        database = dict()
        new_link(message)
    elif message.text == "✂️ Delete existing link":
        delete_link(message)
    elif message.text == "📝 List of your links":
        with connection as db:
            cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            answer_message = db_funcs.get_all_connections(cursor, message.from_user.id)
            if answer_message:
                bot.send_message(message.chat.id, answer_message, reply_markup=keyboard)
            else:
                bot.send_message(message.chat.id, "There are no links", reply_markup=keyboard)
            cursor.close()


def new_link(message):
    message_one = "Please, show me title of the channel you want to repost"
    bot.send_message(message.chat.id, message_one, reply_markup=del_keyboard)
    bot.register_next_step_handler(message, get_channel_name)


@bot.channel_post_handler(func=lambda m: True)
def forward_text(message):
    vk_api = init_session()
    try:
        res = vk_api.wall.post(message=message.text)
    except vk.exceptions.VkAPIError as e:
        vk_api = process_error(e)
        vk_api.wall.post(message=message.text)


def process_error(e):
    if e.code == 5:
        # wrong_token
        return vk.API(vk.Session(access_token=vk_token),  v='5.131')
    if e.code == 6:
        time.sleep(0.05)
        return init_session()
    if e.code == 7:
#         no permission
        return init_session()
    if e.code == 10:
#         inner mistake
        return init_session()
    if e.code == 14:
        # capcha
        return init_session()


@bot.channel_post_handler(content_types=["photo"])
def forward_photo(message):
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
    database['channel_name'] = message.text
    if not is_channel_admin(message.from_user.id, message.text):
        not_admin_message = "Вы не являетесь администратором этого канала"
        bot.send_message(message.chat.id, not_admin_message, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Please, show me vk link", reply_markup=del_keyboard)
        bot.register_next_step_handler(message, get_vk_link)


def get_vk_link(message):
    database['vk_access_token'] = message.text
    with connection as db:
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        db_funcs.add_new_line(cursor, database['channel_name'], database['vk_access_token'], message.from_user.id)
        complete_message = "Your link successfully added!! 🎉🎉🎉 \n Choose your action"
        cursor.close()
    bot.send_message(message.chat.id, complete_message, reply_markup=keyboard)


def delete_link(message):
    message_one = "Please, show me number of the channel you want to delete"
    bot.send_message(message.chat.id, message_one, reply_markup=del_keyboard)
    bot.register_next_step_handler(message, delete_current_link)


def delete_current_link(message):
    if int(message.text) <= len(database):
        del database[int(message.text) - 1]
        bot.send_message(message.chat.id, "Successfully deleted 🎉🎉🎉 \n Choose your action", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "You was wrong in your number. Please, try again", reply_markup=keyboard)


def is_channel_admin(user_id, channel_id):
    return True

bot.infinity_polling()


