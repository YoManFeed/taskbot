import asyncio
from start import router, dp, bot, on_startup
import modules.send_message

admin_id2name = {
    655709388: 'Павел',
    5230124868: 'Галя',
    5079460449: "Наташа",
    5543921382: 'Бабушка',
    975033707: 'Ирина',
    }

user_id2name = {
    655709388: 'Паша',
    6149264921: "Стёпа",
    6506710299: 'Ваня',
    6590628396: 'Артём',
    2122137288: 'Миша',
}

user_name2id = {v: k for k, v in user_id2name.items()}
admin_name2id = {v: k for k, v in admin_id2name.items()}

num_tasks_show = 2

async def main():
    dp.include_router(router)
    print(modules.send_message)
    await bot.delete_webhook(drop_pending_updates=True)
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
