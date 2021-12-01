import os
import threading

if not os.path.isfile('.env'):
    raise RuntimeError('.env file does not exist')

from bot import bot
from server import server

bot_t = threading.Thread(target=bot.infinity_polling)
server_t = threading.Thread(
    target=server.run,
    kwargs={'host': '0.0.0.0', 'port': '8443'}
)

bot_t.start()
server_t.start()
