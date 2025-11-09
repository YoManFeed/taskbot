tasks = [{'task_id': 1, 'giver_id': 655709388, 'tg_name': 'Popit', 'admin_name': 'Павел', 'task_type': 'hard', 'award': 100, 'description': 'asfd', 'number_of_competitors': 0, 'competitors_ids': '', 'target': 1, 'target_ids': '655709388, 6149264921, 6506710299, 2122137288', 'target_names': 'Паша, Стёпа, Ваня, Миша', 'number_of_completions': 0, 'completed_by_id': '', 'max_competitors': 4, 'is_shown': 1, 'is_closed': 0, 'created_at': '2025-06-17 16:19:28', 'completed_at': None}, {'task_id': 2, 'giver_id': 655709388, 'tg_name': 'Popit', 'admin_name': 'Павел', 'task_type': 'legendary', 'award': 7, 'description': '1234567', 'number_of_competitors': 0, 'competitors_ids': '', 'target': 1, 'target_ids': '655709388, 6149264921, 6506710299, 6590628396, 2122137288', 'target_names': 'Паша, Стёпа, Ваня, Артём, Миша', 'number_of_completions': 0, 'completed_by_id': '', 'max_competitors': 7, 'is_shown': 1, 'is_closed': 0, 'created_at': '2025-06-17 16:24:16', 'completed_at': None}]

num_tasks_show = 2
type2rus = {
    'easy': '🟢 Простое 🟢',
    'normal': '🔵 Среднее 🔵',
    'hard': '🔴 Сложное 🔴',
    'legendary': '🟠 Легендарное 🟠'
}

edit_task_keys = {
    'task_id': 'Задание',
    'target_names': "Выполняют",
    'description': "Описание",
    'task_type': "Тип",
    'award': "Вознаграждение",
    'max_competitors': "Количество выполнений"
}

# def create_response(some_dict, keys2ru, initial_text='', end_text='', page=0):
#     response = initial_text + "\n"
#     for idx, task in enumerate(some_dict[page * num_tasks_show:(page + 1) * num_tasks_show], start=1):
#         for key, ru_key in keys2ru.items():
#             if ru_key == 'Задание ID':
#                 value = idx + page * num_tasks_show
#             elif key == 'task_type':
#                 value = type2rus.get(task['task_type'], 'Не указано')
#             else:
#                 value = task.get(key, 'Не указано')
#             response += f"{ru_key}: {value}\n"
#         response += '\n'

#     response += f"Страница {page + 1} из {((len(some_dict) - 1) // num_tasks_show) + 1}\n"
    
#     return response

def create_response(tasks, keys2ru, formatters=None, initial_text='', end_text='', page=0):
    response = initial_text + "\n"
    formatters = formatters or {}

    # постранично
    paged_tasks = tasks[page * num_tasks_show:(page + 1) * num_tasks_show]

    for idx, task in enumerate(paged_tasks, start=1):
        for key, ru_key in keys2ru.items():
            if key in formatters:
                value = formatters[key](task, idx, page)
            else:
                value = task.get(key, 'Не указано')
            
            if value is None:
                continue
            
            response += f"{ru_key}: {value}\n"
        response += '\n'

    response += f"Страница {page + 1} из {((len(tasks) - 1) // num_tasks_show) + 1}\n"
    return response
