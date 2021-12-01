import logging
import time

import db
from dotenv import dotenv_values
import psycopg2.extras
import requests
import telebot
import vk

config = dotenv_values('.env')
process_env = config.get('PROCESS_ENV', 'PRODUCTION')
AVAILABLE_STATUSES_IN_CHANNELS = ('creator', 'administrator')

if process_env == 'DEBUG':
    vk.logger.setLevel(logging.DEBUG)
    telebot.logger.setLevel(logging.DEBUG)


VK_AUTH_BASE_URL = 'https://oauth.vk.com/authorize?'
tg_token = config['SNF_BOT_TELEGRAM_TOKEN']
vk_app_id = config['SNF_BOT_VK_APP_ID']
vk_token_wrong = 'e0bb9661300067cbac41606ea905c2f49aa7db5d5e0e14f34fa31207283c96e38314d9dc59f2e07b17341'  # noqa E501
bot = telebot.TeleBot(tg_token, parse_mode=None)


def init_session(token):
    session = vk.Session(access_token=token)
    vk_api = vk.API(session,  v='5.131')
    return vk_api


@bot.message_handler(commands=['start', 'menu'])
def main(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    register_key = telebot.types.KeyboardButton("Register new link")
    delete_key = telebot.types.KeyboardButton("Delete existing link")
    list_key = telebot.types.KeyboardButton("List of your links")
    keyboard.add(register_key)
    keyboard.add(delete_key)
    keyboard.add(list_key)
    bot.send_message(message.chat.id, "Choose action", reply_markup=keyboard)


@bot.message_handler(content_types=['text'])
def text_parse(message):
    if message.text == "Register new link":
        global database
        database = dict()
        new_link(message)
    elif message.text == "Delete existing link":
        delete_link(message)
    elif message.text == "List of your links":
        with db.connection as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            answer_message = db.get_all_connections(
                cursor,
                message.from_user.id
            )

            if answer_message:
                bot.send_message(message.chat.id, answer_message)
            else:
                bot.send_message(message.chat.id, "There are no links")

            cursor.close()


def new_link(message):
    invitation = 'Please, show me title of the channel you want to repost' \
        ' in format @<channel_name>'
    bot.send_message(message.chat.id, invitation)
    bot.register_next_step_handler(message, get_channel_name)


@bot.channel_post_handler(func=lambda m: True)
def forward_text(message):
    channel_id = message.chat.id

    with db.connection as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            SELECT vk_access_token
            FROM channel_to_vk
            WHERE channel_id = %s
        ''', (channel_id,))
        token = cur.fetchone()['vk_access_token']

    vk_api = init_session(token)

    try:
        vk_api.wall.post(message=message.text)
    except vk.exceptions.VkAPIError as e:
        vk_api = process_error(e)
        vk_api.wall.post(message=message.text)


def process_error(e):
    if e.code == 5:
        # wrong_token
        # TODO:
        # - Сохранить пост в базу
        #   (лучше так, потому что их, потенциально, может быть несколько,
        #   до того, как пользователь обновит токен)
        # - Отправить пользователю сообщение с просьбой перелогинится по-новой
        # - После перелогина отправить все отложенные посты
        return vk.API(vk.Session(access_token=vk_token),  v='5.131')
    if e.code == 6:
        time.sleep(0.05)
        return init_session()
    if e.code == 7:
        # no permission
        # TODO: аналогично пункту с неправильным токеном
        return init_session()
    if e.code == 10:
        # inner mistake
        return init_session()
    if e.code == 14:
        # capcha
        # TODO: Аналогично пункту с неправильным токеном,
        # но, вместо просьбы перелогина, отправлять просьбу пройти капчу
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
    photo_id = vk_api.photos.saveWallPhoto(
        server=resp['server'],
        photo=resp['photo'],
        hash=resp['hash']
    )

    photo_id = photo_id[0]
    photo_id = 'photo' + str(photo_id['owner_id']) + '_' + str(photo_id['id'])

    vk_api.wall.post(attachments=photo_id, message=message.caption)


def get_channel_name(message):
    try:
        channel = bot.get_chat(message.text)
        user_status = bot.get_chat_member(channel.id, message.from_user.id).status
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(
            message.chat.id,
            'This channel does not exists. Try again'
        )
        return
    if user_status in AVAILABLE_STATUSES_IN_CHANNELS:
        with db.connection as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute('''
                INSERT INTO channel_to_vk
                (channel_id, issued_by) VALUES
                (%s, %s)
            ''', (channel.id, message.chat.id))

            vk_auth_url = get_vk_auth_url(channel.id, message.chat.id)
        bot.send_message(
            message.chat.id,
            f'Please, log in to VK via link: {vk_auth_url}'
        )
    else:
        bot.send_message(message.chat.id, "You are not administrator of this channel")


def delete_link(message):
    message_one = "Please, show me number of the channel you want to delete"
    bot.send_message(message.chat.id, message_one)
    bot.register_next_step_handler(message, delete_current_link)


def delete_current_link(message):
    if int(message.text) <= len(database):
        bot.send_message(
            message.chat.id,
            "Successfully deleted\n Choose your action"
        )
    else:
        bot.send_message(
            message.chat.id,
            "You was wrong in your number. Please, try again"
        )


def get_vk_auth_url(channel_id, user_id):
    # TODO: Move redirect_url to environment
    return f'{VK_AUTH_BASE_URL}' \
        f'client_id={vk_app_id}' \
        'display=page&' \
        'redirect_uri=http://localhost:8443/vk_auth&' \
        'scope=wall,photos&' \
        'response_type=token&' \
        f'state={channel_id}_{user_id}&' \
        'v=5.131'
