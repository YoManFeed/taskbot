from start import router, user_db, task_db, admin_db, bot, proof_db

from aiogram.filters.callback_data import CallbackData
from aiogram.filters import StateFilter


from aiogram import F, types
from aiogram.types import Message, CallbackQuery

from aiogram.fsm.state import State, StatesGroup

from aiogram.fsm.context import FSMContext

from main import user_id2name, num_tasks_show, admin_id2name, user_name2id
from keyboards.admin import build_target_keyboard, cancel_keyboard, admin_keyboard, task_type_keyboard, type2rus, arrows_keyboard, proof_action_keyboard


class AdminStates(StatesGroup):
    main = State()

    class AddTask(StatesGroup):
        waiting_target = State()
        waiting_description = State()
        waiting_task_type = State()
        waiting_award = State()
        waiting_competitors_count = State()

    class ConfirmTask(StatesGroup):
        view_tasks = State()
        checking_proof = State()

    class EditTask(StatesGroup):
        pass

    class MyTasks(StatesGroup):
        view_tasks = State()
    
    class DeleteTask(StatesGroup):
        view_tasks = State()
        waiting_task_id = State()

@router.message(F.text == "✅ Добавить задачу")
async def handle_target(message: types.Message, state: FSMContext):
    await state.update_data(target=[])
    await message.answer("Введите для кого это задание:", reply_markup=build_target_keyboard([]))
    await state.set_state(AdminStates.AddTask.waiting_target)

@router.callback_query(AdminStates.AddTask.waiting_target, F.data.startswith("toggle_name:"))
async def toggle_name(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target = data.get("target", [])

    name = callback.data.split(":", 1)[1]

    if name in target:
        target.remove(name)
    else:
        target.append(name)

    await state.update_data(target=target)
    await callback.message.edit_reply_markup(reply_markup=build_target_keyboard(target))
    await callback.answer()

@router.callback_query(AdminStates.AddTask.waiting_target, F.data == "select_all")
async def select_all(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(target=list(user_name2id.keys()).copy())
    await callback.message.edit_reply_markup(reply_markup=build_target_keyboard(list(user_name2id.keys())))
    await callback.answer()

@router.callback_query(AdminStates.AddTask.waiting_target, F.data == "deselect_all")
async def deselect_all(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(target=[])
    await callback.message.edit_reply_markup(reply_markup=build_target_keyboard([]))
    await callback.answer()

@router.callback_query(AdminStates.AddTask.waiting_target, F.data == "confirm")
async def confirm_selection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target = data.get("target", [])

    if not target:
        await callback.message.answer("Выберите хотя бы одно имя!")
        await callback.answer()  # обязательно, чтобы убрать "часики"
        return

    await state.update_data(target=target)

    # удалим ненужную клавиатуру
    await callback.message.edit_reply_markup(reply_markup=None)
    # и укажем, что пользователь ввёл
    await callback.message.answer("Вы указали: " + ', '.join(target), reply_markup=None)

    await callback.message.answer("Введите описание задачи:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.AddTask.waiting_description)

    await callback.answer()


@router.message(AdminStates.AddTask.waiting_description)
async def handle_award(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await message.answer("Введите тип задания:", reply_markup=task_type_keyboard())
    await state.set_state(AdminStates.AddTask.waiting_task_type)

@router.callback_query(AdminStates.AddTask.waiting_task_type, F.data.startswith("task_type:"))
async def handle_task_type(callback: CallbackQuery, state: FSMContext):
    task_type = callback.data.split(":", 1)[1]
    await state.update_data(task_type=task_type)

     # удалим ненужную клавиатуру
    await callback.message.edit_reply_markup(reply_markup=None)
    # и укажем, что пользователь ввёл
    await callback.message.answer(f"Вы указали: {type2rus[task_type]}", reply_markup=None)

    await callback.message.answer("Введите вознаграждение за выполнение задачи:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.AddTask.waiting_award)
    await callback.answer()


@router.message(AdminStates.AddTask.waiting_award)
async def handle_competitors_count(message: types.Message, state: FSMContext):
    award=message.text.strip()
    try:
        award = int(award)
    except ValueError:
        await message.answer("Ошибка: введите ЧИСЛО для награды.", reply_markup=cancel_keyboard())
        return
    
    if award <= 0:
        await message.answer("Ошибка: награда должна быть положительной :)", reply_markup=cancel_keyboard())
        return
    
    await state.update_data(award=award)
    await message.answer("Введите количество выполнений задачи:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.AddTask.waiting_competitors_count)


@router.message(AdminStates.AddTask.waiting_competitors_count)
async def handle_confirm(message: types.Message, state: FSMContext):
    try:
        max_competitors_count = int(message.text.strip())

        if max_competitors_count <= 0:
            await message.answer("Ошибка: количество участников должно быть положительным числом.", reply_markup=cancel_keyboard())
            return

        # await state.update_data(competitors_count=competitors_count)

        data = await state.get_data()

        if max_competitors_count < len(data['target']):
            await message.answer(f"Ошибка: задание выдано {len(data['target'])} детям. Количество раз должно быть не меньше количества выбранных детей. То есть хотя бы {len(data['target'])}.", reply_markup=cancel_keyboard())
            return

        if len(data['target']) == len(user_name2id.keys()):
            target_ids = list(user_name2id.values())
            target_names = list(user_name2id.keys())
            target = False
        else:
            target_ids = [user_name2id[name] for name in data['target']]
            target_names = data['target']
            target = True

        task_data = {
            'giver_id': message.from_user.id,
            'tg_name': message.from_user.full_name,
            'admin_name': admin_id2name.get(message.from_user.id, 'Unknown'),

            'task_type': data['task_type'],
            'award': data['award'],
            'description': data['description'],

            'max_competitors': max_competitors_count,

            'target': target,
            'target_id': ', '.join(map(str, target_ids)),
            'target_names': ', '.join(target_names),
            }

        await task_db.add_task(task_data)
        await message.answer("Задача успешно добавлена!", reply_markup=admin_keyboard())
        await state.set_state(AdminStates.main)
    except ValueError:
        await message.answer("Ошибка: введите ЧИСЛО для награды.", reply_markup=cancel_keyboard())

######################################################## не удалять
# @router.message(F.text.lower() == "📝 редактировать задачу")
# async def handle_edit_task(message: types.Message, state: FSMContext):
#     # await state.set_state(AdminStates.EditTask.view_tasks)
#     tasks = await task_db.get_task()
    
#     if not tasks:
#         await message.answer("Нет задач для редактирования.", reply_markup=admin_keyboard())
#         await state.set_state(AdminStates.main)
#         return

#     text = "Выберите задачу для редактирования:\n"
#     for i, task in enumerate(tasks, start=1):
#         text += f"{i}. {task['description']} (Тип: {type2rus[task['task_type']]})\n"

#     await message.answer(text, reply_markup=build_target_keyboard([task['description'] for task in tasks]))
######################################################## не удалять


from test import create_response


@router.message(F.text.lower() == "все задачи")
async def test_handle_all_tasks(message: types.Message, state: FSMContext):
    tasks = await task_db.get_task(filters=None)

    if not tasks:
        await message.answer("Нет задач для отображения.", reply_markup=admin_keyboard())
        await state.set_state(AdminStates.main)
        return

    keys2ru = {
        'task_id': 'ID задачи',
        'giver_id': 'ID создателя',
        'tg_name': 'Имя создателя',
        'admin_name': 'Имя администратора',
        'task_type': 'Тип задачи',
        'award': 'Вознаграждение',
        'description': 'Описание',
        'number_of_competitors': 'Количество участников',
        'competitors_ids': 'ID участников',
        'target': 'Цель задания',
        'target_ids': 'ID цели',
        'target_names': 'Имена цели',
        'number_of_completions': 'Количество выполнений',
        'completed_by_id': 'ID завершивших',
        'max_competitors': 'Макс. участников',
        'is_shown': 'Показано?',
        'is_closed': 'Закрыто?',
        'created_at': 'Создано в',
        'completed_at': 'Завершено в'
    }
    response = create_response(
        tasks,
        keys2ru=keys2ru,
        initial_text="Список всех задач:", 
        end_text="Выберите задачу для редактирования или удаления.",
        page=0
    )

    await message.answer(response, reply_markup=admin_keyboard())

@router.message(StateFilter(AdminStates.MyTasks.view_tasks), F.text.lower() == "просмотреть мои задачи")
async def view_my_tasks(message: types.Message, state: FSMContext):

    filters = {'giver_id': message.from_user.id, 'is_closed': False}
    tasks = await task_db.get_task(filters=filters)

    if not tasks:
        await message.answer("у вас нет активных заданий.", reply_markup=admin_keyboard())
        await state.set_state(AdminStates.main)
        return

    await state.set_state(AdminStates.MyTasks.view_tasks)
    await state.update_data(tasks=tasks, page=0)
    await show_my_tasks(message, state, initial_text="Ваши активные задачи:")

async def show_my_tasks(message: types.Message, state: FSMContext, initial_text=''):
    data = await state.get_data()
    tasks = data.get('tasks')
    page = data.get('page')

    keys2ru = {
        'task_id': 'ID задачи',
        # 'giver_id': 'ID создателя',
        # 'tg_name': 'Имя создателя',
        # 'admin_name': 'Имя администратора',
        'task_type': 'Тип задачи',
        'award': 'Вознаграждение',
        'description': 'Описание',
        'number_of_competitors': 'Количество участников',
        # 'competitors_ids': 'ID участников',
        # 'target': 'Цель задания',
        # 'target_ids': 'ID цели',
        'target_names': 'Имена цели',
        'number_of_completions': 'Количество выполнений',
        'completed_by_id': 'ID завершивших',
        # 'max_competitors': 'Макс. участников',
        # 'is_shown': 'Показано?',
        # 'is_closed': 'Закрыто?',
        # 'created_at': 'Создано в',
        # 'completed_at': 'Завершено в'
    }

    current_state = await state.get_state()
    if current_state == AdminStates.MyTasks.view_tasks:
        pass
    elif current_state == AdminStates.DeleteTask.view_tasks:
        await state.set_state(AdminStates.DeleteTask.waiting_task_id)
    elif current_state == AdminStates.DeleteTask.waiting_task_id:
        pass
    else:
        await message.answer("Неизвестное состояние. Пожалуйста, попробуйте снова.")
        raise ValueError("Unknown state in show_my_tasks")
    
    response = create_response(
        tasks,
        keys2ru=keys2ru,
        initial_text=initial_text, 
        # end_text="Выберите задачу для редактирования или удаления.",
        page=page
    )

    keyboard = arrows_keyboard(page, len(tasks), num_tasks_show)
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.answer(response, reply_markup=reply_markup)


@router.message(AdminStates.main, F.text == "❌ Удалить задачу")
async def delete_task(message: types.Message, state: FSMContext):
    filters = {'giver_id': message.from_user.id, 'is_closed': False}
    tasks = await task_db.get_task(filters=filters)

    if not tasks:
        await message.answer("у вас нет активных заданий.", reply_markup=admin_keyboard())
        await state.set_state(AdminStates.main)
        return

    await state.set_state(AdminStates.DeleteTask.view_tasks)
    await state.update_data(tasks=tasks, page=0)
    await show_my_tasks(message, state, initial_text="Введите ID задачи для удаления:")

@router.message(AdminStates.DeleteTask.waiting_task_id, F.text.regexp(r"^\d+$"))
async def select_task(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tasks = data['tasks']
    # user_id = message.from_user.id
    # user = (await user_db.get_user(user_id))
    # number_of_tasks = len(user['took_tasks_ids'])
    # if number_of_tasks >= 4:  # TODO пофиксить на нужное число задач
    #     await message.answer("Ты уже взял четыре задачи. Заверши одну из них, чтобы взять новую.")
    #     await state.set_state(UserStates.main)
    #     return

    try:
        selected_index = int(message.text)
    except ValueError:
        await message.answer('Напиши номер задачи, которую хочешь удалить.')
        return

    if selected_index < 1 or selected_index > len(tasks) or isinstance(selected_index, int) is False: # почему то на строки не реагирует
        await message.answer("Такой задачи нет.")
        return
    
    selected_task = tasks[selected_index - 1]

    # # вроде это не должно выполняться, потому что tasks уже возвращают только те задачи, которые доступны для пользователя
    # if selected_task.get("target") and str(user_id) not in selected_task.get("target_ids", "").replace(',', ' ').split():
    #     await message.answer("Как ты вообще угадал номер этой задачи?! Она же не отображается в списке. Окей, пофиг, умный разработчик предусмотрел это и поэтому ты не можешь взять эту задачу. Она предназначена для другого пользователя.")
    #     return

    await task_db.delete_task(selected_task['task_id'])
    await message.answer(f"Задача {selected_task['task_id']} успешно удалена.", reply_markup=admin_keyboard())
    await state.set_state(AdminStates.main)



@router.message(AdminStates.ConfirmTask.view_tasks, F.text.regexp(r"^\d+$"))
async def handle_selected_task(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tasks = data['tasks']

    try:
        selected_index = int(message.text)
    except ValueError:
        await message.answer('Напиши номер задачи, которую хочешь проверить.')
        return

    if selected_index < 1 or selected_index > len(tasks) or isinstance(selected_index, int) is False: # почему то на строки не реагирует
        await message.answer("Такой задачи нет.")
        return
    
    selected_task = tasks[selected_index - 1]

    task_id=selected_task['task_id']
    proof_id=selected_task['proof_id']
    user_id=selected_task['user_id']
    
    # Сохраняем выбранную задачу в state
    await state.update_data(task_id=task_id, proof_id=proof_id, user_id=user_id, description=selected_task['description'], award=selected_task['award'])
    await state.set_state(AdminStates.ConfirmTask.checking_proof)

    # Пытаемся переслать сообщение-доказательство
    await message.answer('Вот доказательство:')
    try:
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=selected_task['chat_id'],
            message_id=selected_task['msg_id']
        )
    except Exception as e:
        await message.answer("❗ Не удалось переслать доказательство.")
        print(f"Ошибка при пересылке сообщения: {e}")
        return

    # Показываем клавиатуру с действиями
    await message.answer(
        text=f"Проверка задачи: {selected_task['description']}\nНаграда: {selected_task['award']} руб.",
        reply_markup=proof_action_keyboard()
    )

def get_money_keyboard(admin_name, money):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=f"Да, мне нужны эти {money} рублей", callback_data="need_money")],
            [types.InlineKeyboardButton(text=f"Пусть {admin_name} оставит их себе", callback_data="save_money")],
        ]
    )

@router.callback_query(F.data == "approve_proof", StateFilter(AdminStates.ConfirmTask.checking_proof))
async def handle_approve(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data['task_id']
    proof_id = data['proof_id']
    user_id = data['user_id']
    admin_name = admin_id2name.get(callback.from_user.id, 'Unknown Admin')

    await proof_db.delete_proof(proof_id)
    await task_db.add_completion(task_id, user_id)

    await bot.send_message(
        chat_id=user_id,
        text=f"Задача {task_id} от {admin_name} успешно принята! 💰\nХотите получить свои {data['award']}?",
        reply_markup=get_money_keyboard(admin_name, money=data['award'])
    )

    await bot.send_message(
        chat_id=callback.from_user.id,
        text=f"Теперь ребёнку решать брать или не брать деньги за выполнение задачи.\nОтправил в главное меню"
    )
    await callback.message.edit_reply_markup()
    await state.set_state(AdminStates.main)

@router.callback_query(F.data == "redo_proof", StateFilter(AdminStates.ConfirmTask.checking_proof))
async def handle_redo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data['user_id']
    proof_id = data['proof_id']
    description = data['description']
    award = data['award']
    task_id = data['task_id']

    await proof_db.delete_proof(proof_id)
    await task_db.delete_competitor(task_id, user_id)

    await bot.send_message(
        chat_id=user_id,
        text=f"🔄 Запрошено повторное доказательство для задачи\n{description}\nнаграда: {award}"
    )

    # 

    await callback.message.edit_reply_markup()
    await state.set_state(AdminStates.main)

