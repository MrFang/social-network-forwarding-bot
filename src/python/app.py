import psycopg2
import telebot
import requests
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

bot = telebot.TeleBot(config['SNF_BOT_TELEGRAM_TOKEN'], parse_mode=None)
access_token = config['SNF_BOT_VK_TOKEN']  # TODO: move to DB

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


