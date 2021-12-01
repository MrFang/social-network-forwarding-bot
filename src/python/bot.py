import logging
import os
import time

import db
from dotenv import dotenv_values
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
bot = telebot.TeleBot(tg_token, parse_mode=None)

no_keyboard = telebot.types.ReplyKeyboardRemove()

keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
register_key = telebot.types.KeyboardButton("🖇 Register new link")
delete_key = telebot.types.KeyboardButton("✂️ Delete existing link")
list_key = telebot.types.KeyboardButton("📝 List of your links")
keyboard.add(register_key)
keyboard.add(delete_key)
keyboard.add(list_key)

social_network_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
vk_key = telebot.types.KeyboardButton("🆕 VK")
inst_key = telebot.types.KeyboardButton("🔜 Instagram")
social_network_keyboard.row(vk_key, inst_key)



def init_session(token):
    session = vk.Session(access_token=token)
    vk_api = vk.API(session,  v='5.131')
    return vk_api


@bot.message_handler(commands=['start', 'menu'])
def main(message):
    bot.send_message(message.chat.id, "Choose action", reply_markup=keyboard)


@bot.message_handler(content_types=['text'])
def text_parse(message):
    if message.text == "🖇 Register new link":
        choose_message = "Please, choose the social network you want to connect with your telegram channel"
        bot.send_message(message.chat.id, choose_message, reply_markup=social_network_keyboard)
    elif message.text == "✂️ Delete existing link":
        delete_link(message)
    elif message.text == "📝 List of your links":
        answer_message = db.get_all_connections(bot, message.from_user.id)
        if answer_message:
            bot.send_message(message.chat.id, answer_message)
        else:
            bot.send_message(message.chat.id, "There are no links")
    elif message.text == "🆕 VK":
        new_link(message)
    elif message.text == "🔜 Instagram":
        inst_message = "Sorry, now we are waiting the approve from Instagram to use our bot \n" \
                      "This function will be soon!"
        bot.send_message(message.chat.id, inst_message, reply_markup=keyboard)

def new_link(message):
    invitation = 'Please, show me title of the channel you want to repost' \
        ' in format @<channel_name>'
    bot.send_message(message.chat.id, invitation, reply_markup=no_keyboard)
    bot.register_next_step_handler(message, get_channel_name)


@bot.channel_post_handler(func=lambda m: True)
def forward_text(message):
    send_post(message.text, message.chat.id)


def process_error(error, from_channel, post_text):
    if error.code in [5, 7]:
        # wrong_token, no_permission
        # TODO: Обработка нетекстовых постов
        # TODO: Пометить в базе, что мы ждём ссылки от этого пользователя
        #       В общем хэндлере тектовых сообщений добавить ветку
        #       для обработки этой ссылки
        db.defer_post(from_channel, post_text)
        owner_id = db.get_telegram_user_by_channel_id(from_channel)
        bot.send_message(owner_id, 'Your token seems to be expired')
        ask_user_auth(owner_id, from_channel)

    if error.code in [6, 10]:
        # Too many requests, inner mistake
        db.defer_post(from_channel, post_text)
        time.sleep(1)
        resend_deferred_posts(from_channel)

    if error.code == 14:
        # capcha
        # TODO
        pass


def download_file(file_id, dest_folder):
    if not os.path.exists(dest_folder):
        vk.logger.warn('MAKEDIRS')
        os.makedirs(dest_folder)

    source_path = bot.get_file(file_id).file_path
    download_link = \
        f'https://api.telegram.org/file/bot{tg_token}/{source_path}'
    filename = download_link.split('/')[-1]
    dest_path = os.path.join(dest_folder, filename)

    download_response = requests.get(download_link, stream=True)

    if download_response.ok:
        open(dest_path, 'wb').write(download_response.content)

    return dest_path


@bot.channel_post_handler(content_types=["photo"])
def forward_photo(message):
    file_id = message.photo[-1].file_id
    filename = download_file(file_id, 'tmp')
    token = db.get_vk_auth_token(message.chat.id)
    vk_api = init_session(token)
    vk_photo_server = vk_api.photos.getWallUploadServer()
    upload_url = vk_photo_server['upload_url']
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

    vk_api = init_session(db.get_vk_auth_token(message.chat.id))
    vk_video_server = vk_api.video.save()
    upload_url = vk_video_server['upload_url']
    open(filename, 'wb').write(download_response.content)
    video = {'video_file': (filename, open(filename, 'rb'))}

    resp = requests.post(upload_url, files=video).json()

    video_id = 'video' + str(resp['owner_id']) + '_' + str(resp['video_id'])

    vk_api.wall.post(attachments=video_id, message=message.caption)


@bot.channel_post_handler(content_types=["document"])
def forward_doc(message):
    file_id = message.document.file_id
    file_path = bot.get_file(file_id).file_path
    download_link = f'https://api.telegram.org/file/bot{tg_token}/{file_path}'

    filename = download_link.split('/')[-1]
    download_response = requests.get(download_link,  allow_redirects=True)

    vk_api = init_session(db.get_vk_auth_token(message.chat.id))
    vk_docs_server = vk_api.docs.getWallUploadServer()
    upload_url = vk_docs_server['upload_url']
    open(filename, 'wb').write(download_response.content)
    doc = {'file': (filename, open(filename, 'rb'))}

    resp = requests.post(upload_url, files=doc).json()
    save_res = vk_api.docs.save(file=resp['file'])
    save_res = save_res['doc']
    doc_id = 'doc' + str(save_res['owner_id']) + '_' + str(save_res['id'])

    vk_api.wall.post(attachments=doc_id, message=message.caption)


def get_channel_name(message):
    if not message.text.startswith('@'):
        print(message.text)
        bot.send_message(message.chat.id, "Wrong format of channel name, start it from @", reply_markup=keyboard)
        return
    try:
        channel = bot.get_chat(message.text)
        user_status = bot.get_chat_member(
            channel.id,
            message.from_user.id
        ).status
        if db.channel_is_exist(channel.id):
            bot.send_message(message.chat.id, "This channel is already linked", reply_markup=keyboard)
            return
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(
            message.chat.id,
            'This channel does not exists. Try again',
            reply_markup=keyboard
        )
        return

    if user_status in AVAILABLE_STATUSES_IN_CHANNELS:
        db.add_new_record(channel.id, message.chat.id)
        ask_user_auth(message.chat.id, channel.id)
        bot.register_next_step_handler(message, parse_vk_auth_url_message)
    else:
        bot.send_message(
            message.chat.id,
            "You are not administrator of this channel",
            reply_markup=keyboard
        )


def parse_vk_auth_url_message(message):
    (channel_id, access_token) = parse_vk_auth_link(message.text)
    db.save_access_token(channel_id, access_token, message.chat.id)
    resend_deferred_posts(channel_id)
    bot.send_message(
        message.chat.id,
        'Registration completed. Thank you!',
        reply_markup=keyboard
    )


def delete_link(message):
    list_of_links = db.get_all_connections(bot, message.from_user.id)
    if not list_of_links:
        no_links_message = "You have not any link. " \
            "To delete link, you need to create link..."
        bot.send_message(
            message.chat.id,
            no_links_message,
            reply_markup=keyboard
        )
    else:
        delete_choose_message = f"You have this links:\n{list_of_links}\n" \
            f"Please, show me number of the channel you want to delete"
        bot.send_message(
            message.chat.id,
            delete_choose_message,
            reply_markup=no_keyboard
        )
        bot.register_next_step_handler(message, delete_current_link)


def delete_current_link(message):
    data_count = db.data_count(message.from_user.id)
    if int(message.text) <= data_count:
        try:
            db.delete_line(message.from_user.id, int(message.text))
            bot.send_message(
                message.chat.id,
                "Successfully deleted 🎉 \n Choose your action",
                reply_markup=keyboard
            )
        except Exception:
            bot.send_message(
                message.chat.id,
                "Error during deleting",
                reply_markup=keyboard
            )
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
        'scope=wall,photos,video,docs&' \
        'response_type=token&' \
        f'state={channel_id}&' \
        'v=5.131'


def ask_user_auth(chat_id, channel_id):
    url = get_vk_auth_url(channel_id)
    bot.send_message(
        chat_id,
        f'Please, log in to VK via <a href="{url}"><b>link</b></a>. \n'
        'Then give me url from your browser address field',
        reply_markup=no_keyboard,
        parse_mode="HTML"
    )


def parse_vk_auth_link(link):
    hash = link.split('#')[1]
    params = hash.split('&')
    data = {}

    for param in params:
        if param.startswith('access_token='):
            data['access_token'] = param.split('=')[1]

        if param.startswith('state='):
            data['channel_id'] = int(param.split('=')[1])

    return (data['channel_id'], data['access_token'])


def send_post(post_text, from_channel):
    access_token = db.get_vk_auth_token(from_channel)
    vk_api = init_session(access_token)

    try:
        vk_api.wall.post(message=post_text)
    except vk.exceptions.VkAPIError as error:
        process_error(error, from_channel, post_text)


def resend_deferred_posts(channel_id):
    posts = db.get_deferred_posts(channel_id)
    [send_post(post, channel_id) for post in posts]
