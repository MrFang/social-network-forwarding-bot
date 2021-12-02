import os

if not os.path.isfile('.env'):
    raise RuntimeError('.env file does not exist')

from bot import bot

bot.infinity_polling()
