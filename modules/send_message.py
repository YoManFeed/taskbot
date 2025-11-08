from aiogram.filters import Command
from start import router, user_db, task_db, admin_db, bot, proof_db

from aiogram.filters.callback_data import CallbackData

from aiogram import F, types
from aiogram.types import Message, CallbackQuery

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from modules.user import UserStates, user_keyboard
from modules.admin import AdminStates, admin_keyboard, arrows_keyboard
from modules.admin import show_my_tasks
from keyboards.admin import proof_action_keyboard

from aiogram.filters.state import StateFilter


from datetime import datetime
import time

import os
import re

from main import user_id2name as user_ids 
from main import admin_id2name as admins_ids, num_tasks_show

from test import create_response


# class AdminStates(StatesGroup):
#     main = State()
#     add_task = State()
#     edit_task = State()
#     delete_task = State()
#     view_tasks = State()
#     view_task_details = State()
#     confirm_delete_task = State()

# class UserStates(StatesGroup):
#     main = State()
#     view_tasks = State()
#     sending_proof = State()
#     choosing_task = State()

# class AddTaskStates(StatesGroup):
#     description = State()
#     award = State()

# def admin_keyboard():
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [
#                 KeyboardButton(text="✅ Добавить задачу"),
#                 KeyboardButton(text="Выполненные задачи")
#             ],
#             [
#                 KeyboardButton(text="Редактировать задачу"),
#                 KeyboardButton(text="Просмотреть мои задачи"),
#                 KeyboardButton(text='❌ Удалить задачу')
#             ]
#         ],
#         resize_keyboard=True
#     )

# def user_keyboard():
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [
#                 KeyboardButton(text="✅ Взять задачу"),
#                 KeyboardButton(text="Просмотреть мои задачи")
#             ],
#             [
#                 KeyboardButton(text="Мой баланс"),
#                 KeyboardButton(text="Завершить задачу")
#             ]
#         ],
#         resize_keyboard=True
#     )

def cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="cancel")]]
    )

def quick_check_keyboard(proof_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👀 Проверить сейчас", callback_data=f"quick_check:{proof_id}")],
            [InlineKeyboardButton(text="📋 Все доказательства", callback_data="list_proofs")]
        ]
    )

@router.message(Command(commands=["start", "help"]))
async def send_welcome(message: Message, state: FSMContext):
    await message.answer(
        "Привет! Я бот, который дает задания от родителей."
    )
    new_user_id = message.from_user.id
    user_name = message.from_user.full_name
    if new_user_id not in user_ids and new_user_id not in admins_ids:
        await message.answer("Ты не из семьи Попытовых.\nЕсли ты Лёша, то свяжись с Пашей через Иришу")
        return
    
    if new_user_id in user_ids:
        await message.answer('Доброе утро, работяга.', reply_markup=user_keyboard())
        await user_db.add_user(new_user_id, user_name)
        await state.set_state(UserStates.main)

    if new_user_id in admins_ids:
        await message.answer('Доброе утро, работодатель.', reply_markup=admin_keyboard())
        await admin_db.add_admin(new_user_id, user_name)
        await state.set_state(AdminStates.main)


@router.callback_query(F.data == "cancel")
async def cancel_tasks(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    await callback.message.answer(f'Это из колбека, твой текущий стейт: {current_state}')
    if current_state is None:
        await callback.answer("Что? Как у тебя это получилось? Сообщи о баге разработчику.")
        return

    await state.clear()

    if current_state.startswith("AddTaskStates"):
        await callback.message.answer("Добавление задачи отменено.", reply_markup=admin_keyboard())
        await state.set_state(AdminStates.main)

    elif current_state.startswith("AdminStates"):
        await state.set_state(AdminStates.main)

    elif current_state.startswith("UserStates"):
        if current_state == "UserStates.TakeTask:view_tasks": # изменить на waiting_for_task_id
            # Чистое удаление сообщения с задачами:
            try:
                await callback.message.delete()
            except:
                pass
        await callback.message.answer("Действие отменено.", reply_markup=user_keyboard())
        await state.set_state(UserStates.main)

    else:
        await callback.message.answer("Действие отменено.", reply_markup=admin_keyboard())
        await state.set_state(AdminStates.main)

    await callback.message.answer(f'изменил стейт на {await state.get_state()}')
    await callback.answer()

# @router.message(AddTaskStates.description)
# async def add_task_description(message: types.Message, state: FSMContext):
#     await state.update_data(description=message.text.strip())
#     await message.answer("Введите награду (в рублях):", reply_markup=cancel_keyboard())
#     await state.set_state(AddTaskStates.award)

# @router.message(AdminStates.AddTask.award)
# async def add_task_award(message: types.Message, state: FSMContext):
#     try:
#         award = int(message.text.strip())
#         await state.update_data(award=award)

#         data = await state.get_data()

#         task_data = {
#             'giver_id': message.from_user.id,
#             'tg_name': admins_ids.get(message.from_user.id, 'Unknown'),
#             'award': data['award'],
#             'description': data['description'],
#             'competitors_ids': []
#         }

#         await task_db.add_task(task_data)
#         await message.answer("Задача успешно добавлена!", reply_markup=admin_keyboard())
#         await state.set_state(AdminStates.main)
#     except ValueError:
#         await message.answer("Ошибка: введите число для награды.", reply_markup=cancel_keyboard())

@router.message(F.text == "✅ Взять задачу")
async def complete_task(message: types.Message, state: FSMContext):
    filters = {
        "is_shown": True,
        "available_for_user": message.from_user.id
    }
    tasks = await task_db.get_task(filters=filters)

    if not tasks:
        await message.answer("Нет доступных задач.")
        return

    await state.set_state(UserStates.TakeTask.view_tasks)
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

@router.callback_query(F.data.in_(["prev_page", "next_page"]))
async def paginate_tasks(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data['page']

    if callback.data == "prev_page" and page > 0:
        page -= 1
    elif callback.data == "next_page":
        total_pages = (len(data['tasks']) - 1) // num_tasks_show + 1
        if page < total_pages - 1:
            page += 1

    await state.update_data(page=page)
    await callback.message.delete()
    current_state = await state.get_state()
    if current_state.startswith("UserStates.TakeTask:"):
        await send_tasks_page(callback.message, state)

    elif current_state.startswith("AdminStates.MyTasks:"):
        await show_my_tasks(callback.message, state)
    
    elif current_state == AdminStates.DeleteTask.waiting_task_id:
        await show_my_tasks(callback.message, state, initial_text="Введите ID задачи для удаления:")
    
    elif current_state == UserStates.CompleteTask.view_tasks:
        await send_tasks_page(callback.message, state)

    elif current_state == UserStates.MyTasks.view_tasks:
        await send_tasks_page(callback.message, state)
    
    elif current_state == AdminStates.ConfirmTask.view_tasks:
        await send_tasks_page(callback.message, state)

    else:
        print(f"Unexpected state: {await state.get_state()}")

@router.message(UserStates.TakeTask.view_tasks, F.text.regexp(r"^\d+$"))
async def select_task(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tasks = data['tasks']
    user_id = message.from_user.id
    user = (await user_db.get_user(user_id))
    number_of_tasks = len(user['took_tasks_ids'])
    if number_of_tasks >= 4000:  # TODO пофиксить на нужное число задач
        await message.answer("Ты уже взял четыре задачи. Заверши одну из них, чтобы взять новую.")
        await state.set_state(UserStates.main)
        return

    try:
        selected_index = int(message.text)
    except ValueError:
        await message.answer('Напиши номер задачи, которую хочешь выполнить.')
        return

    if selected_index < 1 or selected_index > len(tasks) or isinstance(selected_index, int) is False: # почему то на строки не реагирует
        await message.answer("Такой задачи нет.")
        return
    
    selected_task = tasks[selected_index - 1]

    # вроде это не должно выполняться, потому что tasks уже возвращают только те задачи, которые доступны для пользователя
    if selected_task.get("target") and str(user_id) not in selected_task.get("target_ids", "").replace(',', ' ').split():
        await message.answer("Как ты вообще угадал номер этой задачи?! Она же не отображается в списке. Окей, пофиг, умный разработчик предусмотрел это и поэтому ты не можешь взять эту задачу. Она предназначена для другого пользователя.")
        return

    if str(message.from_user.id) not in selected_task['competitors_ids']:
        await task_db.add_competitor(task_id=selected_task['task_id'], competitor_id=message.from_user.id)
        await user_db.add_task(user_id=message.from_user.id, task_id=selected_task['task_id'])
        await message.answer(f"Ты взял задачу!")
        await state.set_state(UserStates.main)
    else:
        await message.answer("Ты уже взял эту задачу.")
        return

# @router.message(F.text.lower() == 'завершить задачу')
# async def complete_task_user(message: types.Message, state: FSMContext):
#     """Юзер из списка выбранных задач просит завершить одну из них.
#     Создателю задачи переотправляется сообщение с просьбой завершить задачу. 
#     И доказательствами выполнение задачи от пользователя.
#     """
#     user_id = message.from_user.id
#     user = await user_db.get_user(user_id)
#     tasks_ids = user['took_tasks_ids']

#     if not tasks_ids:
#         await message.answer("У тебя нет взятых задач.")
#         return

#     tasks_ids = tasks_ids.split()
#     tasks_ids = list(map(int, tasks_ids))
#     print(f"Tasks IDs: {tasks_ids}")
#     tasks = await task_db.get_task_description_award_by_id(task_ids=tasks_ids)

#     await state.update_data(tasks=tasks)

#     response = "Выбери номер задачи, которую хочешь завершить:\n"
#     for idx, task in enumerate(tasks, start=1):
#         response += f"{idx}. {task['description']}\nНаграда: {task['award']} руб.\n"

#     await message.answer(response, reply_markup=cancel_keyboard())
#     await state.set_state(UserStates.CompleteTask.view_tasks)
@router.message(StateFilter(UserStates.main), F.text.lower() == 'завершить задачу')
async def complete_task_user(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = await user_db.get_user(user_id)
    tasks_ids = user['took_tasks_ids']

    if not tasks_ids:
        await message.answer("У тебя нет взятых задач.")
        return

    tasks_ids = list(map(int, tasks_ids.split()))
    tasks = await task_db.get_task(filters={"task_ids": tasks_ids})

    await state.set_state(UserStates.CompleteTask.view_tasks)
    await state.update_data(tasks=tasks, page=0)
    await send_tasks_page(message, state)


@router.message(UserStates.CompleteTask.view_tasks, F.text.regexp(r"^\d+$"))
async def choose_task(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tasks = data['tasks']

    selected_index = int(message.text)

    if selected_index < 1 or selected_index > len(tasks):
        await message.answer("Некорректный номер задачи. Попробуй ещё раз.")
        return

    selected_task = tasks[selected_index - 1]

    # Сохраняем выбранную задачу в FSM
    await state.update_data(selected_task=selected_task)

    await message.answer("Отправь доказательства выполнения задачи (можно текст, фото, документ).")
    await state.set_state(UserStates.CompleteTask.sending_proof)

@router.message(UserStates.CompleteTask.sending_proof)
async def send_proof(message: types.Message, state: FSMContext):
    data = await state.get_data()
    selected_task = data['selected_task']
    task_id = selected_task['task_id']
    giver_id = selected_task['giver_id']
    user_id = message.from_user.id

    # Проверка: уже ли есть пруф от этого юзера по этой задаче
    already_sent = await proof_db.has_proof(task_id=task_id, user_id=user_id)
    if already_sent:
        await message.answer("Ты уже отправлял доказательства по этой задаче.\nТы был переведён в глвное меню")
        await state.set_state(UserStates.main)
        return

    # Сохраняем доказательство
    proof_id = await proof_db.add_proof(
        task_id=task_id,
        giver_id=giver_id,
        user_id=user_id,
        chat_id=message.chat.id,
        msg_id=message.message_id
    )

    # Получаем имя пользователя
    user = await user_db.get_user(user_id)
    user_name = user.get('user_name', 'Пользователь')

    # Отправляем сообщение создателю задачи
    await bot.send_message(
        chat_id=giver_id,
        text=(
            f"Пользователь {user_name} отправил доказательства по задаче:\n"
            f"<b>{selected_task['description']}</b>\n"
            f"Нажми кнопку, чтобы проверить задачу прямо сейчас."
        ),
        parse_mode='HTML',
        reply_markup=quick_check_keyboard(proof_id)
    )
    # await message.send_copy(chat_id=giver_id)

    await message.answer("Доказательства отправлены автору задачи на проверку.")
    await state.set_state(UserStates.main)


# @router.message(UserStates.CompleteTask.sending_proof)
# async def send_proof(message: types.Message, state: FSMContext):
#     data = await state.get_data()
#     selected_task = data['selected_task']

#     creator_id = selected_task['giver_id']  # <-- предположим, что в task хранится id автора задачи

#     user_id = message.from_user.id
#     user = await user_db.get_user(user_id)
#     user_name = user['user_name']
#     await bot.send_message(
#         chat_id=creator_id,
#         text=f"Пользователь {user_name} отправил доказательства по задаче: {selected_task['description']}"
#         )

#     # Пересылаем сообщение создателю задачи
#     await message.send_copy(chat_id=creator_id)

#     await message.answer("Доказательства отправлены автору задачи на проверку. Ожидай подтверждения.")

#     await state.set_state(UserStates.main)

@router.message(F.text.lower() == 'мой баланс')
async def view_balance(message: types.Message, state: FSMContext):
    """Работяга узнает свой баланс"""
    user = await user_db.get_user(message.from_user.id)
    balance = user['balance']
    response = f"Ваш баланс: {balance} руб."
    await message.answer(response, reply_markup=user_keyboard())


@router.message(AdminStates.main, F.text.lower() == 'просмотреть мои задачи')
async def view_my_tasks_admin(message: types.Message, state: FSMContext):
    tasks = await task_db.get_my_non_completed_tasks(user_id=message.from_user.id)
    if not tasks:
        await message.answer("Тут пусто :(")
        return

    response = "Список ещё не завершенных задач:\n"
    for task in tasks:
        response += f"{task['description']}\nНаграда: {task['award']} руб.\n"
        if task['competitors_ids']:
            competitors_names = [user_ids.get(int(cid), 'Неизвестный') for cid in task['competitors_ids'].split()]
            response += f"Задачу выполняют: {', '.join(competitors_names)}\n\n"
        else:
            response += '\n'

    await message.answer(response, reply_markup=admin_keyboard())
    await state.set_state(AdminStates.main)


@router.message(UserStates.main, F.text.lower() == 'просмотреть мои задачи')
async def view_my_tasks_user(message: types.Message, state: FSMContext):
    tasks_ids = await user_db.get_non_completed_tasks(user_id=message.from_user.id)
    tasks = await task_db.get_task_description_award_by_id(task_ids=tasks_ids)

    if not tasks:
        await message.answer("Ты лоботряс :(")
        await state.set_state(UserStates.main)
        return

    response = "Список ещё не завершенных задач:\n"
    for task in tasks:
        response += f"{task['description']}\nНаграда: {task['award']} руб.\n"
        response += '\n'

    await message.answer(response, reply_markup=user_keyboard())
    await state.set_state(UserStates.main)

@router.message(F.text.lower() == 'admin state')
async def admin_state(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins_ids:
        await message.answer("У вас нет доступа к этой команде.")
        await state.set_state(UserStates.main)
        return

    await message.answer("Вы в админском меню.", reply_markup=admin_keyboard())
    await state.set_state(AdminStates.main)

@router.message(F.text.lower() == 'user state')
async def user_state(message: types.Message, state: FSMContext):
    if message.from_user.id not in user_ids:
        await message.answer("У вас нет доступа к этой команде.")
        return

    await message.answer("Вы в пользовательском меню.", reply_markup=user_keyboard())
    await state.set_state(UserStates.main)


@router.message(F.text == "all database")
async def view_all_database(message: types.Message, state: FSMContext):
    users = await user_db.get_all_users()
    tasks = await task_db.get_all_tasks()
    admins = await admin_db.get_all_admins()

    print('~' * 20)
    print('Пользователи:')
    print(users)
    print('~' * 20)
    print('Задачи:')
    print(tasks)
    print('~' * 20)
    print("Админы")
    print(admins)
    print('~' * 20)

    response = "Администраторы:\n"
    for admin in admins:
        for key, value in admin.items():
            response += f"{key}: {value}\n"
        response += "\n"
    
    response += "\n"

    response += "Пользователи:\n"
    for user in users:
        for key, value in user.items():
            response += f"{key}: {value}\n"
        response += "\n"
    
    response += "\n"

    response += "\nЗадачи:\n"
    for task in tasks:
        for key, value in task.items():
            response += f"{key}: {value}\n"
        response += "\n"

    await message.answer(response, reply_markup=admin_keyboard())
    await state.set_state(AdminStates.main)


@router.callback_query(F.data.startswith("quick_check:"))
async def quick_check_proof(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in admins_ids:
        await callback.answer("У вас нет доступа к этой задаче.", show_alert=True)
        return

    _, proof_id_raw = callback.data.split(":", 1)
    if not proof_id_raw.isdigit():
        await callback.answer("Некорректный запрос.", show_alert=True)
        return

    proof_id = int(proof_id_raw)
    proof = await proof_db.get_proof_by_id(proof_id)

    if not proof or proof['giver_id'] != callback.from_user.id:
        if callback.message.reply_markup:
            await callback.message.edit_reply_markup()
        await callback.answer("Доказательство уже проверено или недоступно.", show_alert=True)
        return

    tasks = await task_db.get_task(filters={"task_ids": [proof['task_id']]})
    if not tasks:
        await callback.answer("Задача не найдена.", show_alert=True)
        return

    task = tasks[0]

    await state.update_data(
        task_id=task['task_id'],
        proof_id=proof_id,
        user_id=proof['user_id'],
        description=task['description'],
        award=task['award']
    )
    await state.set_state(AdminStates.ConfirmTask.checking_proof)

    if callback.message.reply_markup:
        await callback.message.edit_reply_markup()

    await callback.message.answer("Вот доказательство:")
    try:
        await bot.copy_message(
            chat_id=callback.message.chat.id,
            from_chat_id=proof['chat_id'],
            message_id=proof['msg_id']
        )
    except Exception as e:
        await callback.message.answer("❗ Не удалось переслать доказательство.")
        print(f"Ошибка при пересылке сообщения (quick_check): {e}")
        await callback.answer("Не удалось переслать доказательство.", show_alert=True)
        return

    await callback.message.answer(
        text=f"Проверка задачи: {task['description']}\nНаграда: {task['award']} руб.",
        reply_markup=proof_action_keyboard()
    )
    await callback.answer()


async def show_pending_proofs_for_admin(admin_id: int, target_message: types.Message, state: FSMContext):
    proofs = await proof_db.get_proofs_by_giver(admin_id)

    if not proofs:
        await target_message.answer("Нет новых выполненных задач.")
        return False

    task_ids = [proof['task_id'] for proof in proofs]
    tasks = await task_db.get_task(filters={"task_ids": task_ids}) if task_ids else []
    task_by_id = {task["task_id"]: task for task in tasks}

    combined = []
    for proof in proofs:
        task = task_by_id.get(proof["task_id"])
        if task:
            combined.append({
                **proof,
                "task_type": task["task_type"],
                "description": task["description"],
                "award": task["award"],
                "user_id": proof["user_id"]
            })

    if not combined:
        await target_message.answer("Нет новых выполненных задач.")
        return False

    await state.set_state(AdminStates.ConfirmTask.view_tasks)
    await state.update_data(tasks=combined, page=0)
    await send_tasks_page(target_message, state)
    return True


@router.callback_query(F.data == "list_proofs")
async def list_proofs(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in admins_ids:
        await callback.answer("У вас нет доступа.", show_alert=True)
        return

    success = await show_pending_proofs_for_admin(callback.from_user.id, callback.message, state)
    if not success:
        await callback.answer("Новых выполненных задач нет.", show_alert=True)
    else:
        await callback.answer()


@router.message(StateFilter(AdminStates.main), F.text.lower() == "выполненные задачи")
async def view_completed_tasks(message: types.Message, state: FSMContext):
    await show_pending_proofs_for_admin(message.from_user.id, message, state)

# combined: 
# [
#     {
#         'proof_id': 1,
#         'task_id': 10, 
#         'giver_id': 655709388, 
#         'user_id': 655709388, 
#         'chat_id': 655709388, 
#         'msg_id': 2706, 
#         'created_at': '2025-06-23 08:47:41', 
#         'task_type': 'easy', 
#         'description': 'Доделай бота 2', 
#         'award': 10
#         }, 
#     {
#         'proof_id': 2,
#         'task_id': 2, 
#         'giver_id': 655709388, 
#         'user_id': 655709388, 
#         'chat_id': 655709388, 
#         'msg_id': 2838, 
#         'created_at': '2025-06-23 10:25:24', 
#         'task_type': 'legendary', 
#         'description': '1234567', 
#         'award': 7
#     }, 
#     {
#         'proof_id': 3, 
#         'task_id': 4, 
#         'giver_id': 655709388, 
#         'user_id': 655709388, 
#         'chat_id': 655709388, 
#         'msg_id': 2859, 
#         'created_at': '2025-06-23 10:26:28', 
#         'task_type': 'easy', 
#         'description': 'оно должно пропасть', 
#         'award': 1
#     }
# ]


@router.callback_query(F.data == "need_money", StateFilter(UserStates))
async def need_money(callback: CallbackQuery, state: FSMContext):
    # проблема в том, информация о балансе хранится в тексте кнопки. 
    # надо получить текст с кнопки, а потом уже парсить его
    message_text = callback.message.text

    pattern = r"Задача \d+ от (\w+) успешно принята! 💰\nХотите получить свои (\d+)\?"
    match = re.search(pattern, message_text)

    admin_name = match.group(1)  # Имя отправителя задачи
    award = int(match.group(2))  # Сумма награды

    user_id = callback.from_user.id

    await user_db.add_money(user_id, award)

    print(f"ПОПОЛНЕНИЕ БАЛАНСА: {admin_name}: {award} рублей для {user_ids.get(user_id, 'Неизвестный пользователь')} (ID: {user_id})")

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(f"Ваш баланс пополнился!", reply_markup=user_keyboard())
    await state.set_state(UserStates.main)
    await callback.answer()


@router.callback_query(F.data == "save_money", StateFilter(UserStates))
async def need_money(callback: CallbackQuery, state: FSMContext):

    await callback.message.answer(f"Вы очень бескорыстный человек!", reply_markup=user_keyboard())
    await state.set_state(UserStates.main)
    await callback.answer()
