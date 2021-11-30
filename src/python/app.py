import psycopg2
import psycopg2.extras
import telebot
import db_funcs
import requests
from dotenv import dotenv_values
import os

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



bot = telebot.TeleBot(config['SNF_BOT_TELEGRAM_TOKEN'], parse_mode=None)
access_token = config['SNF_BOT_VK_TOKEN']  # TODO: move to DB


database = dict()

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
        global database
        database = dict()
        new_link(message)
    elif message.text == "Delete existing link":
        delete_link(message)
    elif message.text == "List of your links":
        with connection as db:
            cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            answer_message = db_funcs.get_all_connections(cursor, message.from_user.id)
            if answer_message:
                bot.send_message(message.chat.id, answer_message)
            else:
                bot.send_message(message.chat.id, "There are no links")
            cursor.close()

def new_link(message):
    message_one = "Please, show me title of the channel you want to repost"
    bot.send_message(message.chat.id, message_one)
    bot.register_next_step_handler(message, get_channel_name)

def get_channel_name(message):
    database['channel_name'] = message.text
    bot.send_message(message.chat.id, "Please, show me vk link")
    bot.register_next_step_handler(message, get_vk_link)

def get_vk_link(message):
    database['vk_access_token'] = message.text
    with connection as db:
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        db_funcs.add_new_line(cursor, database['channel_name'], database['vk_access_token'], message.from_user.id)
        complete_message = "Your link successfully added!! \n Choose your action"
        cursor.close()
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


