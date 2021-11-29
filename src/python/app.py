import psycopg2
import telebot
import requests
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
access_token = config['SNF_BOT_VK_TOKEN']  # TODO: move to DB


@bot.message_handler(func=lambda m: True)
def echo_all(message):
    requests.post('https://api.vk.com/method/wall.post?'
                  'v=5.131&'
                  'owner_id=89685577&'  # TODO move to DB
                  f'message={message.text}&'
                  f'access_token={access_token}'
                  )


bot.infinity_polling()
