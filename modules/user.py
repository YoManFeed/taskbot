from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from start import router
from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from start import task_db
from test import create_response
from keyboards.admin import arrows_keyboard

from main import num_tasks_show
from main import user_id2name as user_ids 



class UserStates(StatesGroup):
    main = State()

    class TakeTask(StatesGroup):
        view_tasks = State()
        waiting_for_task_id = State()

    class MyTasks(StatesGroup):
        view_tasks = State()

    class CompleteTask(StatesGroup):
        view_tasks = State()
        sending_proof = State()

    class MyBalance(StatesGroup):
        pass

def user_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✅ Взять задачу"),
                KeyboardButton(text="Просмотреть мои задачи")
            ],
            [
                KeyboardButton(text="Мой баланс"),
                KeyboardButton(text="Завершить задачу")
            ]
        ],
        resize_keyboard=True
    )

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )

@router.message(StateFilter(UserStates.main), F.text.lower() == "просмотреть мои задачи")
async def view_my_tasks_user(message: types.Message, state: FSMContext):
    filters = {
        'taken_by_user': str(message.from_user.id),  # важно: id как строка, т.к. хранятся в текстовом поле
        'is_closed': False
    }

    tasks = await task_db.get_task(filters=filters)

    if not tasks:
        await message.answer("У вас нет активных задач.")
        await state.set_state(UserStates.main)
        return

    await state.set_state(UserStates.MyTasks.view_tasks)
    await state.update_data(tasks=tasks, page=0)
    await send_tasks_page(message, state)

async def send_tasks_page(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tasks = data['tasks']
    page = data['page']

    type2rus = {
        'easy': '🟢 Простое 🟢',
        'normal': '🔵 Среднее 🔵',
        'hard': '🔴 Сложное 🔴',
        'legendary': '🟠 Легендарное 🟠'
    }

    response = create_response(
    tasks,
    keys2ru={
        'task_id': 'Задание ID',
        'task_type': "Тип",
        'admin_name': "Создатель",
        'description': "Описание",
        'award': "Вознаграждение",
        'competitors_ids': "Выполняют",
    },
    formatters = {
        "task_id": lambda task, idx, page: idx + page * num_tasks_show,
        "task_type": lambda task, idx, page: type2rus.get(task["task_type"], "Не указано"),
        "description": lambda task, idx, page: task.get("description", "Не указано"),
        "admin_name": lambda task, idx, page: task.get("admin_name", "Не указано"),
        "award": lambda task, idx, page: f"{task.get('award', 0)} руб.",
        "competitors_ids": lambda task, idx, page: (
            None if task.get("max_competitors", 1) == 1 else
            f"{', '.join(user_ids.get(int(uid), '???') for uid in task.get('competitors_ids', '').split(',') if uid)}"
        ),
    },
    initial_text="Выберите номер задачи, которую хотите выполнить.\nВы можете выполнять не более четырёх задач одновременно.\n",
    page=page
)

    keyboard = arrows_keyboard(page, len(tasks), num_tasks_show)
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.answer(response, reply_markup=reply_markup)
    # await state.set_state(UserStates.TakeTask.waiting_for_task_id)