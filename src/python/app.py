import psycopg2
import telebot
import argparse
import requests

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
access_token = 'ad4d25a8ac7c44f965775921500543db4172658217066e97abd6571aa0802fc78d087d300d996cee8443d'

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    requests.post(f'https://api.vk.com/method/wall.post?v=5.131?owner_id=89685577&message={message.text}&access_token={access_token}')


bot.infinity_polling()
