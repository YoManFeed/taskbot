from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from start import router

from main import user_name2id

type2rus = {
    "easy": "🟢 Простое 🟢",
    "normal": "🔵 Среднее 🔵",
    "hard": "🔴 Сложное 🔴",
    "legendary": "🟠 Легендарное 🟠"
}

rus2type = {v: k for k, v in type2rus.items()}

def cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="cancel")]]
    )

def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✅ Добавить задачу"),
                KeyboardButton(text="Выполненные задачи")
            ],
            [
                KeyboardButton(text="📝 Редактировать задачу"),
                KeyboardButton(text="Просмотреть мои задачи"),
                KeyboardButton(text='❌ Удалить задачу')
            ]
        ],
        resize_keyboard=True
    )


def build_target_keyboard(selected_names):
    keyboard = []

    for name in list(user_name2id.keys()):
        if name in selected_names:
            button_text = f"✅ {name}"
        else:
            button_text = f"☑ {name}"
        keyboard.append(
            [InlineKeyboardButton(text=button_text, callback_data=f"toggle_name:{name}")]
        )

    # логика кнопки "Все / Убрать всех"
    if set(selected_names) == set(user_name2id.keys()):
        all_button_text = "Убрать всех 💨"
        all_button_callback = "deselect_all"
    else:
        all_button_text = "🧑‍🧑‍🧒‍🧒 Все"
        all_button_callback = "select_all"

    keyboard.append(
        [InlineKeyboardButton(text=all_button_text, callback_data=all_button_callback)]
    )

    keyboard.append(
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm")]
    )

    keyboard.append(
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def task_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Простое 🟢", callback_data="task_type:easy"),
                InlineKeyboardButton(text="🔵 Среднее 🔵", callback_data="task_type:normal")
            ],
            [
                InlineKeyboardButton(text="🔴 Сложное 🔴", callback_data="task_type:hard"),
                InlineKeyboardButton(text="🟠 Легендарное 🟠", callback_data="task_type:legendary")
            ]
        ]
    )

def proof_action_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
                [InlineKeyboardButton(text="✅ Принять", callback_data="approve_proof")],
                [InlineKeyboardButton(text="🔄 Переделай", callback_data="redo_proof")],
            ]
        )



def arrows_keyboard(page, n_tasks, num_tasks_show):
    keyboard = []
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data="prev_page"))
    if page < (n_tasks - 1) // num_tasks_show + 1 - 1:
        pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data="next_page"))
    
    keyboard.append(pagination_buttons)
    keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])

    return keyboard