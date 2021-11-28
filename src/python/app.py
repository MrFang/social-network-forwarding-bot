import psycopg2
import telebot
import argparse

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


@bot.message_handler(func=lambda m: True)
def echo_all(message):
    bot.reply_to(message, message.text)


bot.infinity_polling()
