import aiosqlite
from aiosqlite import connect as aioconnect
from datetime import datetime

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, '.databases')

os.makedirs(DATABASE_DIR, exist_ok=True)

user_db_path = os.path.join(DATABASE_DIR, 'user.db')
admin_db_path = os.path.join(DATABASE_DIR, 'admin.db')
task_db_path = os.path.join(DATABASE_DIR, 'task.db')
proof_db_path = os.path.join(DATABASE_DIR, 'proof.db')

SETTINGS_MAP = {
    1: "most_relevant",
    2: "most_popular",
    3: "highest_rated",
    4: "newest"
}

REVERSE_SETTINGS_MAP = {v: k for k, v in SETTINGS_MAP.items()}

class AdminProfileDB:
    def __init__(self, db_path=admin_db_path):
        self.db_path = db_path

    async def initialize(self):
        """
        Создаёт таблицы для хранения данных админов,
        истории и статистики, если их ещё нет.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admin_profiles (
                    admin_id INTEGER PRIMARY KEY,
                    admin_name TEXT DEFAULT NULL
                )
            ''')

    async def add_admin(self, admin_id, admin_name):
        """Добавляет админа в датабазу"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR IGNORE INTO admin_profiles (admin_id, admin_name)
                VALUES (?, ?)
            ''', (admin_id, admin_name))
            await db.commit()

    async def get_all_admins(self):
        """Возвращает всех пользователей из базы данных."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM admin_profiles') as cursor:
                columns = [description[0] for description in cursor.description]
                rows = await cursor.fetchall()
                admins = [dict(zip(columns, row)) for row in rows]
                return admins


class UserProfileDB:
    def __init__(self, db_path=user_db_path):
        self.db_path = db_path

    async def initialize(self):
        """
        Создаёт таблицы для хранения данных пользователей,
        истории и статистики, если их ещё нет.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    user_name TEXT DEFAULT '',
                    balance INTEGER DEFAULT 0,
                    took_tasks_ids TEXT DEFAULT '',
                    completed_tasks_ids TEXT DEFAULT '',
                    balance_history TEXT DEFAULT ''
                )
            ''')
    
    async def add_user(self, user_id, user_name):
        """Добавляет воркера в датабазу"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR IGNORE INTO user_profiles (user_id, user_name)
                VALUES (?, ?)
            ''', (user_id, user_name))
            await db.commit()
    
    async def add_task(self, user_id, task_id):
        """Добавляет задачу в список взятых задач пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT took_tasks_ids FROM user_profiles WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    tasks_ids = row[0].split() if row[0] else []
                    tasks_ids.append(str(task_id))
                    tasks_ids_str = ' '.join(tasks_ids).strip()
                    await db.execute('''
                        UPDATE user_profiles
                        SET took_tasks_ids = ?
                        WHERE user_id = ?
                    ''', (tasks_ids_str, user_id))
                else:
                    await db.execute('''
                        INSERT INTO user_profiles (user_id, took_tasks_ids)
                        VALUES (?, ?)
                    ''', (user_id, str(task_id)))
            await db.commit()
    
    async def get_all_users(self):
        """Возвращает всех пользователей из базы данных."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM user_profiles') as cursor:
                columns = [description[0] for description in cursor.description]
                rows = await cursor.fetchall()
                users = [dict(zip(columns, row)) for row in rows]
                return users
    
    async def get_user(self, user_id):
        """Возвращает данные пользователя по его ID."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    async def get_non_completed_tasks(self, user_id):
        """Возвращает все взятые пользователем задачи, которые не завершены."""
        async with aioconnect(self.db_path) as db:
            async with db.execute('''
                SELECT took_tasks_ids FROM user_profiles WHERE user_id = ?
            ''', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    tasks_ids = row[0].split() if row[0] else []
                    return [int(task_id) for task_id in tasks_ids if task_id.isdigit()]                    
                return []
            
    async def add_money(self, user_id, award):
        """Добавляет деньги пользователю."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE user_profiles
                SET balance = balance + ?
                WHERE user_id = ?
            ''', (award, user_id))
            await db.commit()
    
    async def remove_task(self, user_id: int, task_id: int):
        """Удаляет задачу из списка взятых задач пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT took_tasks_ids FROM user_profiles WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return
                tasks_ids = row[0].split() if row[0] else []
                tasks_ids = [tid for tid in tasks_ids if tid != str(task_id)]
                tasks_ids_str = ' '.join(tasks_ids)
                await db.execute(
                    'UPDATE user_profiles SET took_tasks_ids = ? WHERE user_id = ?',
                    (tasks_ids_str, user_id)
                )
            await db.commit()


class TasksDB:
    def __init__(self, db_path=task_db_path):
        self.db_path = db_path

    async def initialize(self):
        """Создаёт таблицу для хранения задач, если её ещё нет."""
        async with aioconnect(self.db_path) as db:
            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                             
                    giver_id INTEGER,
                    tg_name TEXT,
                    admin_name TEXT,
                    
                    task_type TEXT DEFAULT "easy",
                    award INTEGER,
                    description TEXT,

                    number_of_competitors INTEGER DEFAULT 0,
                    competitors_ids TEXT DEFAULT '',

                    target BOOLEAN DEFAULT FALSE,
                    target_ids TEXT DEFAULT '',
                    target_names TEXT DEFAULT '',

                    number_of_completions INTEGER DEFAULT 0,
                    completed_by_id INTEGER DEFAULT '',
                    max_competitors INTEGER,

                    is_shown BOOLEAN DEFAULT TRUE,
                    is_closed BOOLEAN DEFAULT FALSE,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                )
            ''')
            await db.commit()

    async def add_task(self, task_data: dict):
        """Добавляет новую задачу в базу данных."""
        async with aioconnect(self.db_path) as db:
            await db.execute('''
                INSERT INTO tasks (giver_id, tg_name, admin_name, 
                                   task_type, award, description,
                                   max_competitors,
                                   target, target_ids, target_names)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', tuple(
                task_data.get(key, None) for key in [
                    'giver_id', 'tg_name', 'admin_name',
                    'task_type', 'award', 'description',
                    'max_competitors', 
                    'target', 'target_id', 'target_names'
                ]
            ))
            await db.commit()
    
    # напишем функцию get_task с фильтрами, чтобы обобщить несколько 
    # уже существующих функций получения задач
    async def get_task(self, filters=None):
        """
        Возвращает задачи из базы данных с возможностью фильтрации.
        filters: dict, ключи - названия столбцов, значения - условия для фильтрации.
        """
        query = 'SELECT * FROM tasks'
        params = []
        conditions = []
        
        if filters:
            for key, value in filters.items():
                # обрабатываем фильтрацию для показа задач юзеру
                # спец-фильтр: показать задачи для target=FALSE (публичные) или где user_id в target_ids
                if key == "available_for_user":
                    user_id = value
                    conditions.append("(target = FALSE OR (target = TRUE AND target_ids LIKE ?))")
                    params.append(f"%{user_id}%")
                elif key == "taken_by_user":
                    user_id = value
                    conditions.append("competitors_ids LIKE ?")
                    params.append(f"%{user_id}%")
                elif key == "task_ids":
                    placeholders = ','.join(['?'] * len(value))
                    conditions.append(f"task_id IN ({placeholders})")
                    params.extend(value)
                else:
                    conditions.append(f"{key} = ?")
                    params.append(value)
                # conditions.append(f"{key} = ?")
                # params.append(value)
            query += ' WHERE ' + ' AND '.join(conditions)
        
        async with aioconnect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                columns = [description[0] for description in cursor.description]
                rows = await cursor.fetchall()
                tasks = [dict(zip(columns, row)) for row in rows]
                return tasks


    async def get_all_tasks(self):
        """Возвращает все задачи из базы данных."""
        async with aioconnect(self.db_path) as db:
            async with db.execute('SELECT * FROM tasks') as cursor:
                columns = [description[0] for description in cursor.description]
                rows = await cursor.fetchall()
                tasks = [dict(zip(columns, row)) for row in rows]
                return tasks
    
    async def delete_task(self, task_id):
        """Удаляет задачу из базы данных по её ID."""
        async with aioconnect(self.db_path) as db:
            await db.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
            await db.commit()
    
    # async def get_non_completed_tasks(self):
    #     """Возвращает все незавершенные задачи для пользователя"""
    #     async with aioconnect(self.db_path) as db:
    #         async with db.execute('''
    #             SELECT * FROM tasks WHERE completed_at IS NULL
    #         ''') as cursor:
    #             columns = [description[0] for description in cursor.description]
    #             rows = await cursor.fetchall()
    #             tasks = [dict(zip(columns, row)) for row in rows]
    #             return tasks
    
    async def get_my_non_completed_tasks(self, user_id):
        """Возвращает незавершенные задачи для конкретного админа"""
        async with aioconnect(self.db_path) as db:
            async with db.execute('''
                SELECT * FROM tasks
                WHERE giver_id = ? AND completed_at IS NULL
            ''', (user_id,)) as cursor:
                columns = [description[0] for description in cursor.description]
                rows = await cursor.fetchall()
                tasks = [dict(zip(columns, row)) for row in rows]
                return tasks
    
    # async def get_my_completed_tasks(self, user_id):
    #     """Возвращает незавершенные задачи для конкретного пользователя."""
    #     async with aioconnect(self.db_path) as db:
    #         async with db.execute('''
    #             SELECT * FROM tasks
    #             WHERE giver_id = ? AND сompleted_at IS NOT NULL
    #         ''', (user_id,)) as cursor:
    #             columns = [description[0] for description in cursor.description]
    #             rows = await cursor.fetchall()
    #             tasks = [dict(zip(columns, row)) for row in rows]
    #             return tasks
    
    async def add_competitor(self, task_id, competitor_id):
        """Добавляет участника к задаче, обновляет счётчик и скрывает задачу при необходимости."""        
        async with aioconnect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT number_of_competitors, max_competitors, competitors_ids FROM tasks WHERE task_id = ?',
                (task_id,)
            )
            row = await cursor.fetchone()

            if row is None:
                raise ValueError(f"Задание с task_id={task_id} не найдено")

            current_count, max_count, current_ids = row
            current_count += 1

            # Обновляем список участников
            all_ids = current_ids.strip().split() if current_ids else []
            all_ids.append(str(competitor_id))
            all_ids_str = ' '.join(all_ids)

            # Проверка на достижение лимита
            is_shown = False if current_count >= max_count else True

            # Обновляем запись
            await db.execute('''
                UPDATE tasks
                SET competitors_ids = ?, number_of_competitors = ?, is_shown = ?
                WHERE task_id = ?
            ''', (all_ids_str, current_count, is_shown, task_id))

            await db.commit()
    
    async def add_completion(self, task_id, user_id):
        """Обновляет базу данных в связи с выполнением одной задачи."""
        async with aioconnect(self.db_path) as db:
            # надо увеличить на 1 number_of_completions и если number_of_completions == max_competitors, то is_closed надо поставить на True
            # потом надо добавить user_id в completed_by_id в конец строки
            cursor = await db.execute(
                'SELECT number_of_completions, max_competitors, completed_by_id FROM tasks WHERE task_id = ?',
                (task_id,)
            )
            row = await cursor.fetchone()

            if row is None:
                raise ValueError(f"Задание с task_id={task_id} не найдено")
            
            current_count, max_count, completed_ids = row
            current_count += 1

            # Обновляем список выполненных
            all_ids = str(completed_ids).strip().split() if completed_ids else []
            all_ids.append(str(user_id))
            all_ids_str = ' '.join(all_ids)

            # Проверка на достижение лимита
            is_closed = True if current_count >= max_count else False

            # Обновляем запись
            await db.execute('''
                UPDATE tasks
                SET completed_by_id = ?, number_of_completions = ?, is_closed = ?
                WHERE task_id = ?
            ''', (all_ids_str, current_count, is_closed, task_id))

            await db.commit()


    async def delete_competitor(self, task_id: int, competitor_id: int):
        """Удаляет участника из задачи, обновляет счётчик и флаги видимости."""
        async with aioconnect(self.db_path) as db:
            await db.execute("BEGIN IMMEDIATE")

            cur = await db.execute(
                'SELECT number_of_competitors, competitors_ids, max_competitors, is_closed '
                'FROM tasks WHERE task_id = ?',
                (task_id,)
            )
            row = await cur.fetchone()
            if row is None:
                await db.execute("ROLLBACK")
                raise ValueError(f"Задание с task_id={task_id} не найдено")

            current_count, current_ids, max_competitors, is_closed = row
            current_ids = current_ids or ""

            # убрать id из строки
            def _remove_id_str(current: str, id_: int) -> str:
                s = f" {current.strip()} "
                s = s.replace(f" {id_} ", " ")
                return " ".join(s.split())  # нормализуем пробелы

            new_ids = _remove_id_str(current_ids, competitor_id)

            # не уходить в минус
            new_count = max(0, current_count - 1)

            # задача снова видна, если слотов ещё не набрали и задача не закрыта
            new_is_shown = 1 if (new_count < max_competitors and not is_closed) else 0

            await db.execute(
                'UPDATE tasks SET competitors_ids = ?, number_of_competitors = ?, is_shown = ? '
                'WHERE task_id = ?',
                (new_ids, new_count, new_is_shown, task_id)
            )
            await db.commit()

    # async def delete_competitor(self, task_id, competitor_id):
    #     """Удаляет участника из задачи и обновляет счётчик."""
    #     async with aioconnect(self.db_path) as db:
    #         cursor = await db.execute(
    #             'SELECT number_of_competitors, competitors_ids FROM tasks WHERE task_id = ?',
    #             (task_id,)
    #         )
    #         row = await cursor.fetchone()

    #         if row is None:
    #             raise ValueError(f"Задание с task_id={task_id} не найдено")

    #         current_count, current_ids = row
    #         current_count -= 1

    #         # Обновляем список участников
    #         all_ids = current_ids.strip().split() if current_ids else []
    #         all_ids = [id for id in all_ids if id != str(competitor_id)]
    #         all_ids_str = ' '.join(all_ids)

    #         # # Проверка на достижение лимита
    #         # is_shown = True if current_count < 1 else False

    #         # Обновляем запись
    #         await db.execute('''
    #             UPDATE tasks
    #             SET competitors_ids = ?, number_of_competitors = ?
    #             WHERE task_id = ?
    #         ''', (all_ids_str, current_count, task_id))

    #         await db.commit()

    
    async def get_task_description_award_by_id(self, task_ids):  # TODO переименовать в get_task_by_id
        """Возвращает задачу по её ID."""
        async with aioconnect(self.db_path) as db:
            awards_descriptions = []
            for task_id in task_ids:
                async with db.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,)) as cursor:
                    row = await cursor.fetchone()
                    columns = [description[0] for description in cursor.description]
                    awards_descriptions.append(dict(zip(columns, row)))
            return awards_descriptions
        

class ProofDB:
    def __init__(self, db_path=proof_db_path):
        self.db_path = db_path

    async def initialize(self):
        """Создаёт таблицу для хранения доказательств, если её ещё нет."""
        async with aioconnect(self.db_path) as db:
            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS proofs (
                    proof_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    giver_id INTEGER,
                    user_id INTEGER,
                    chat_id INTEGER,
                    msg_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.commit()
    
    async def has_proof(self, task_id: int, user_id: int) -> bool:
        async with aioconnect(self.db_path) as db:
            async with db.execute(
                'SELECT 1 FROM proofs WHERE task_id = ? AND user_id = ? LIMIT 1',
                (task_id, user_id)
            ) as cursor:
                return await cursor.fetchone() is not None

    async def add_proof(self, task_id: int, giver_id: int, user_id: int, chat_id: int, msg_id: int):
        async with aioconnect(self.db_path) as db:
            cursor = await db.execute(
                '''
                INSERT INTO proofs (task_id, giver_id, user_id, chat_id, msg_id)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (task_id, giver_id, user_id, chat_id, msg_id)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_proof_by_id(self, proof_id: int):
        async with aioconnect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM proofs WHERE proof_id = ?',
                (proof_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
    

    async def get_proofs_by_giver(self, giver_id: int):
        async with aioconnect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM proofs WHERE giver_id = ?',
                (giver_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def delete_proof(self, proof_id):
        """Удаляет задачу из базы данных по её ID."""
        async with aioconnect(self.db_path) as db:
            await db.execute('DELETE FROM proofs WHERE proof_id = ?', (proof_id,))
            await db.commit()
