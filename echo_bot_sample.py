import os

from dotenv import load_dotenv

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import aiohttp

load_dotenv('config.env')
token = os.environ.get("BOT_TOKEN")
print(f"Bot token: {token}")

# bot = Bot(token=os.environ['BOT_TOKEN'])
# dp = Dispatcher(bot)


# @dp.message_handler(commands=['start', 'help'])
# async def send_welcome(message: types.Message):
#     await message.reply("Hi!\nI'm EchoBot!\nPowered by aiogram.")


# @dp.message_handler()
# async def echo(message: types.Message):
#     await message.reply(message.text)


# if __name__ == '__main__':
#     executor.start_polling(dp)
