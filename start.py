import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from database import UserProfileDB, TasksDB, AdminProfileDB, ProofDB


load_dotenv('config.env')
TOKEN = os.getenv('BOT_TOKEN')


bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# admin_db = AdminProfileDB(db_path="admin.db")
# user_db = UserProfileDB(db_path="user.db")
# task_db = TasksDB(db_path="task.db")
admin_db = AdminProfileDB()
user_db = UserProfileDB()
task_db = TasksDB()
proof_db = ProofDB()




async def on_startup():
    await user_db.initialize()
    print("База данных user успешно инициализирована")
    await task_db.initialize()
    print("База данных task успешно инициализирована")
    await admin_db.initialize()
    print("База данных admin успешно инициализирована")
    await proof_db.initialize()
    print("База данных Proof успешно инициализирована")
