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
vk_token_k = '03210b531557fb25665bbe3b37a6eabcc66dd71b1088bb7009ac413ed98fcb76adb0e84c9c967318c6245'
bot = telebot.TeleBot(tg_token, parse_mode=None)

no_keyboard = telebot.types.ReplyKeyboardRemove()
keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)


def init_session(token):
    session = vk.Session(access_token=token)
    vk_api = vk.API(session,  v='5.131')
    return vk_api


@bot.message_handler(commands=['start', 'menu'])
def main(message):
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
        new_link(message)
    elif message.text == "Delete existing link":
        delete_link(message)
    elif message.text == "List of your links":
        answer_message = db.get_all_connections(message.from_user.id)
        if answer_message:
            bot.send_message(message.chat.id, answer_message)
        else:
            bot.send_message(message.chat.id, "There are no links")


def new_link(message):
    invitation = 'Please, show me title of the channel you want to repost' \
        ' in format @<channel_name>'
    bot.send_message(message.chat.id, invitation, reply_markup=no_keyboard)
    bot.register_next_step_handler(message, get_channel_name)


@bot.channel_post_handler(func=lambda m: True)
def forward_text(message):
    vk_api = init_session(vk_token_k)

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
        return vk.API(vk.Session(access_token=vk_token_k),  v='5.131')
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

    vk_api = init_session(vk_token_k)
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


@bot.channel_post_handler(content_types=["video"])
def forward_video(message):
    file_id = message.video.file_id
    file_path = bot.get_file(file_id).file_path
    download_link = f'https://api.telegram.org/file/bot{tg_token}/{file_path}'

    filename = download_link.split('/')[-1]
    download_response = requests.get(download_link,  allow_redirects=True)

    vk_api = init_session(vk_token_k)
    vk_video_server = vk_api.video.save()
    upload_url = vk_video_server['upload_url']
    open(filename, 'wb').write(download_response.content)
    img = {'video_file': (filename, open(filename, 'rb'))}

    resp = requests.post(upload_url, files=img).json()

    video_id = 'video' + str(resp['owner_id']) + '_' + str(resp['video_id'])

    vk_api.wall.post(attachments=video_id, message=message.caption)


def get_channel_name(message):
    try:
        channel = bot.get_chat(message.text)
        user_status = bot.get_chat_member(
            channel.id,
            message.from_user.id
        ).status
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(
            message.chat.id,
            'This channel does not exists. Try again',
            reply_markup=keyboard
        )
        return

    if user_status in AVAILABLE_STATUSES_IN_CHANNELS:
        db.add_new_record(channel.id, message.chat.id)
        vk_auth_url = get_vk_auth_url(channel.id)

        bot.send_message(
            message.chat.id,
            f'Please, log in to VK via <a href="{vk_auth_url}"><b>link</b></a>. \n'
            'Then give me url from your browser address field',
            reply_markup=no_keyboard,
            parse_mode="HTML"
        )
        bot.register_next_step_handler(message, parse_vk_auth_url)
    else:
        bot.send_message(message.chat.id, "You are not administrator of this channel", reply_markup=keyboard)


def parse_vk_auth_url(message):
    hash = message.text.split('#')[1]
    params = hash.split('&')
    data = {}

    for param in params:
        if param.startswith('access_token='):
            data['access_token'] = param.split('=')[1]

        if param.startswith('state='):
            data['channel_id'] = int(param.split('=')[1])

    db.save_access_token(data['channel_id'], data['access_token'], message.chat.id)

    bot.send_message(message.chat.id, 'Registration completed. Thank you!', reply_markup=keyboard)


def delete_link(message):
    list_of_links = db.get_all_connections(message.from_user.id)
    if not list_of_links:
        no_links_message = "You have not any link. To delete link, you need to create link..."
        bot.send_message(message.chat.id, no_links_message, reply_markup=keyboard)
    else:
        delete_choose_message = f"You have this links: \n {list_of_links} \n " \
                                f"Please, show me number of the channel you want to delete"
        bot.send_message(message.chat.id, delete_choose_message, reply_markup=no_keyboard)
        bot.register_next_step_handler(message, delete_current_link)


def delete_current_link(message):
    data_count = db.data_count(message.from_user.id)
    if int(message.text) <= data_count:
        try:
            db.delete_line(message.from_user.id, int(message.text))
            bot.send_message(
                message.chat.id,
                "Successfully deleted \n Choose your action",
                reply_markup=keyboard
            )
        except:
            bot.send_message(message.chat.id, "Error during deleting", reply_markup=keyboard)
    else:
        bot.send_message(
            message.chat.id,
            "You was wrong in your number. Please, try again",
            reply_markup=keyboard
        )


def get_vk_auth_url(channel_id):
    return f'{VK_AUTH_BASE_URL}' \
        f'client_id={vk_app_id}' \
        'display=page&' \
        'redirect_uri=https://oauth.vk.com/blank.html&' \
        'scope=wall,photos&' \
        'response_type=token&' \
        f'state={channel_id}&' \
        'v=5.131'

def get_channel_creator(channel_id):
    admins = bot.get_chat_administrators(channel_id)
    for admin in admins:
        if admin.status == 'creator':
            return admin.user.id