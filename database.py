from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import aiosqlite
import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class CommunityMember(Base):
    __tablename__ = 'community_members'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String(50))
    full_name = Column(String(100))
    skills = Column(Text)  # JSON строка с навыками
    interests = Column(Text)  # JSON строка с интересами
    contact_info = Column(Text)  # JSON строка с контактной информацией

class Database:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.init_database()
        # Инициализация SQLAlchemy
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_connection(self):
        """Создает подключение к базе данных"""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Инициализация базы данных и создание необходимых таблиц"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Таблица пользователей
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    telegram_nick TEXT,
                    occupation TEXT,
                    skills TEXT,
                    company_info TEXT,
                    links TEXT,
                    about TEXT,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP,
                    is_complete BOOLEAN DEFAULT FALSE
                )
                """)
                
                # Таблица контекста сообщений
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """)
                
                # Таблица общих саммари чата
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    summary TEXT,
                    start_timestamp TIMESTAMP,
                    end_timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """)
                
                # Создаем таблицу настроек
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT NOT NULL UNIQUE,
                        value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Добавляем индексы для оптимизации
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_context_user_id ON message_context(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_summaries_user_id ON chat_summaries(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)")
                
                # Проверяем создание таблиц
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                logger.info(f"Созданные таблицы: {[table[0] for table in tables]}")
                
                conn.commit()
                logger.info("База данных успешно инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise

    async def add_or_update_user(self, user_id: int, data: dict) -> bool:
        """Добавляет или обновляет информацию о пользователе"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существование пользователя
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Обновляем существующего пользователя
                    query = """
                    UPDATE users SET 
                        username = COALESCE(?, username),
                        full_name = COALESCE(?, full_name),
                        telegram_nick = COALESCE(?, telegram_nick),
                        occupation = COALESCE(?, occupation),
                        skills = COALESCE(?, skills),
                        company_info = COALESCE(?, company_info),
                        links = COALESCE(?, links),
                        about = COALESCE(?, about),
                        last_active = CURRENT_TIMESTAMP,
                        is_complete = COALESCE(?, is_complete)
                    WHERE user_id = ?
                    """
                else:
                    # Добавляем нового пользователя
                    query = """
                    INSERT INTO users (
                        user_id, username, full_name, telegram_nick, 
                        occupation, skills, company_info, links, about,
                        last_active, is_complete
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    """
                
                # Подготавливаем данные
                params = [
                    data.get('username'),
                    data.get('full_name'),
                    data.get('telegram_nick'),
                    data.get('occupation'),
                    json.dumps(data.get('skills', []), ensure_ascii=False),
                    data.get('company_info'),
                    json.dumps(data.get('links', {}), ensure_ascii=False),
                    data.get('about'),
                    data.get('is_complete', False)
                ]
                
                if exists:
                    params.append(user_id)
                else:
                    params.insert(0, user_id)
                
                cursor.execute(query, params)
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении/обновлении пользователя {user_id}: {e}")
            return False

    async def get_user_info(self, user_id: int) -> Optional[dict]:
        """Получает информацию о пользователе"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT username, full_name, telegram_nick, occupation, 
                       skills, company_info, links, about, is_complete
                FROM users WHERE user_id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'username': row[0],
                        'full_name': row[1],
                        'telegram_nick': row[2],
                        'occupation': row[3],
                        'skills': json.loads(row[4]) if row[4] else [],
                        'company_info': row[5],
                        'links': json.loads(row[6]) if row[6] else {},
                        'about': row[7],
                        'is_complete': bool(row[8])
                    }
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении информации о пользователе {user_id}: {e}")
            return None

    async def add_message_to_context(self, user_id: int, role: str, content: str) -> bool:
        """Добавляет сообщение в контекст пользователя"""
        try:
            logger.info(f"Добавление сообщения в контекст для пользователя {user_id}")
            logger.info(f"Роль: {role}")
            logger.info(f"Содержание: {content[:100]}...")  # Логируем первые 100 символов
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем количество сообщений пользователя
                cursor.execute("SELECT COUNT(*) FROM message_context WHERE user_id = ?", (user_id,))
                count = cursor.fetchone()[0]
                logger.info(f"Текущее количество сообщений пользователя: {count}")
                
                cursor.execute("""
                INSERT INTO message_context (user_id, role, content)
                VALUES (?, ?, ?)
                """, (user_id, role, content))
                conn.commit()
                
                # Проверяем успешность добавления
                cursor.execute("SELECT id FROM message_context WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
                last_id = cursor.fetchone()
                if last_id:
                    logger.info(f"Сообщение успешно добавлено в контекст (id: {last_id[0]})")
                else:
                    logger.warning("Сообщение добавлено, но не удалось получить его ID")
                
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении сообщения в контекст для пользователя {user_id}: {e}")
            return False

    async def get_user_context(self, user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
        """Получает последние сообщения из контекста пользователя"""
        try:
            logger.info(f"Получение контекста для пользователя {user_id} (лимит: {limit})")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем общее количество сообщений
                cursor.execute("SELECT COUNT(*) FROM message_context WHERE user_id = ?", (user_id,))
                total_messages = cursor.fetchone()[0]
                logger.info(f"Всего сообщений в контексте: {total_messages}")
                
                cursor.execute("""
                SELECT role, content, timestamp
                FROM message_context
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """, (user_id, limit))
                
                messages = []
                for row in cursor.fetchall():
                    message = {
                        'role': row[0],
                        'content': row[1],
                        'timestamp': row[2]
                    }
                    messages.append(message)
                    logger.info(f"Получено сообщение: роль={row[0]}, время={row[2]}, содержание={row[1][:50]}...")
                
                logger.info(f"Получено {len(messages)} сообщений из {total_messages}")
                return messages[::-1]  # Возвращаем в хронологическом порядке
                
        except Exception as e:
            logger.error(f"Ошибка при получении контекста пользователя {user_id}: {e}")
            return []

    async def create_chat_summary(self, user_id: int, summary: str) -> bool:
        """Создает новое саммари чата"""
        try:
            logger.info(f"Создание нового саммари для пользователя {user_id}")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем временной диапазон для саммари
                cursor.execute("""
                SELECT MIN(timestamp), MAX(timestamp)
                FROM message_context
                WHERE user_id = ?
                """, (user_id,))
                
                start_time, end_time = cursor.fetchone()
                logger.info(f"Диапазон саммари: {start_time} - {end_time}")
                
                # Добавляем саммари
                cursor.execute("""
                INSERT INTO chat_summaries (
                    user_id, summary, start_timestamp, end_timestamp
                ) VALUES (?, ?, ?, ?)
                """, (user_id, summary, start_time, end_time))
                
                conn.commit()
                logger.info("Саммари успешно создано")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при создании саммари для пользователя {user_id}: {e}")
            return False

    async def get_latest_summary(self, user_id: int) -> Optional[str]:
        """Получает последнее саммари чата для пользователя"""
        try:
            logger.info(f"Получение последнего саммари для пользователя {user_id}")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT summary, created_at
                FROM chat_summaries
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    logger.info(f"Найдено саммари от {row[1]}")
                    logger.info(f"Содержание саммари: {row[0][:100]}...")
                    return row[0]
                else:
                    logger.info("Саммари не найдено")
                    return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении саммари для пользователя {user_id}: {e}")
            return None

    async def search_users_by_skills(self, skills: List[str]) -> List[Dict[str, Any]]:
        """Поиск пользователей по навыкам"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Создаем условие для поиска по навыкам
                skill_conditions = ' OR '.join(['skills LIKE ?' for _ in skills])
                params = [f'%{skill}%' for skill in skills]
                
                query = f"""
                SELECT user_id, username, full_name, telegram_nick, 
                       occupation, skills, company_info
                FROM users
                WHERE {skill_conditions}
                """
                
                cursor.execute(query, params)
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'full_name': row[2],
                        'telegram_nick': row[3],
                        'occupation': row[4],
                        'skills': json.loads(row[5]) if row[5] else [],
                        'company_info': row[6]
                    })
                return users
                
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователей по навыкам: {e}")
            return []

    async def search_users_by_occupation(self, occupation: str) -> List[Dict[str, Any]]:
        """Поиск пользователей по роду деятельности"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT user_id, username, full_name, telegram_nick, 
                       occupation, skills, company_info
                FROM users
                WHERE occupation LIKE ?
                """, (f'%{occupation}%',))
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'full_name': row[2],
                        'telegram_nick': row[3],
                        'occupation': row[4],
                        'skills': json.loads(row[5]) if row[5] else [],
                        'company_info': row[6]
                    })
                return users
                
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователей по роду деятельности: {e}")
            return []

    async def add_member(self, telegram_id, username, full_name, skills, interests, contact_info):
        """Добавление нового участника"""
        session = self.Session()
        try:
            # Проверяем, существует ли уже пользователь
            existing_member = session.query(CommunityMember).filter_by(telegram_id=telegram_id).first()
            if existing_member:
                logger.info(f"Пользователь с telegram_id {telegram_id} уже существует, обновляем данные")
                existing_member.username = username
                existing_member.full_name = full_name
                existing_member.skills = json.dumps(skills)
                existing_member.interests = json.dumps(interests)
                existing_member.contact_info = json.dumps(contact_info)
            else:
                member = CommunityMember(
                    telegram_id=telegram_id,
                    username=username,
                    full_name=full_name,
                    skills=json.dumps(skills),
                    interests=json.dumps(interests),
                    contact_info=json.dumps(contact_info)
                )
                session.add(member)
            
            session.commit()
            logger.info(f"Успешно сохранен пользователь: {full_name}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при сохранении пользователя {full_name}: {str(e)}")
            return False
        finally:
            session.close()

    async def get_member(self, telegram_id):
        """Получение информации об участнике"""
        session = self.Session()
        try:
            member = session.query(CommunityMember).filter_by(telegram_id=telegram_id).first()
            if member:
                return {
                    'telegram_id': member.telegram_id,
                    'username': member.username,
                    'full_name': member.full_name,
                    'skills': json.loads(member.skills),
                    'interests': json.loads(member.interests),
                    'contact_info': json.loads(member.contact_info)
                }
            return None
        finally:
            session.close()

    async def find_members_by_skill(self, skill):
        """Поиск участников по навыку"""
        session = self.Session()
        try:
            members = session.query(CommunityMember).all()
            matching_members = []
            for member in members:
                skills = json.loads(member.skills)
                if skill.lower() in [s.lower() for s in skills]:
                    matching_members.append({
                        'username': member.username,
                        'full_name': member.full_name,
                        'contact_info': json.loads(member.contact_info)
                    })
            return matching_members
        finally:
            session.close()

    async def find_members_by_interest(self, interest):
        """Поиск участников по интересам"""
        session = self.Session()
        try:
            members = session.query(CommunityMember).all()
            matching_members = []
            for member in members:
                interests = json.loads(member.interests)
                if interest.lower() in [i.lower() for i in interests]:
                    matching_members.append({
                        'username': member.username,
                        'full_name': member.full_name,
                        'contact_info': json.loads(member.contact_info)
                    })
            return matching_members
        finally:
            session.close()

    async def update_member(self, telegram_id, **kwargs):
        """Обновление информации об участнике"""
        session = self.Session()
        try:
            member = session.query(CommunityMember).filter_by(telegram_id=telegram_id).first()
            if member:
                for key, value in kwargs.items():
                    if key in ['skills', 'interests', 'contact_info']:
                        value = json.dumps(value)
                    setattr(member, key, value)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    async def get_all_members(self):
        """Получение всех участников"""
        session = self.Session()
        try:
            members = session.query(CommunityMember).all()
            return [{
                'telegram_id': member.telegram_id,
                'username': member.username,
                'full_name': member.full_name,
                'skills': json.loads(member.skills),
                'interests': json.loads(member.interests),
                'contact_info': json.loads(member.contact_info)
            } for member in members]
        finally:
            session.close()

    async def find_members_by_category(self, category):
        """Поиск участников по категории (например, 'разработчик', 'дизайнер' и т.д.)"""
        session = self.Session()
        try:
            members = session.query(CommunityMember).all()
            matching_members = []
            
            # Словарь категорий и связанных с ними ключевых слов
            category_keywords = {
                'разработчик': ['python', 'javascript', 'java', 'react', 'node', 'developer', 'web', 'backend', 'frontend'],
                'дизайнер': ['design', 'ui', 'ux', 'figma', 'photoshop', 'prototype'],
                'менеджер': ['manager', 'management', 'agile', 'scrum', 'team lead', 'product'],
                'маркетолог': ['marketing', 'smm', 'content', 'analytics', 'brand']
            }
            
            # Нормализуем категорию
            category = category.lower()
            
            # Определяем ключевые слова для поиска
            search_keywords = []
            for cat, keywords in category_keywords.items():
                if category in cat.lower() or any(category in keyword.lower() for keyword in keywords):
                    search_keywords.extend(keywords)
            
            # Если нашли ключевые слова, ищем по ним
            if search_keywords:
                for member in members:
                    skills = [s.lower() for s in json.loads(member.skills)]
                    interests = [i.lower() for i in json.loads(member.interests)]
                    
                    # Проверяем совпадение по навыкам или интересам
                    if any(keyword.lower() in skill for keyword in search_keywords for skill in skills) or \
                       any(keyword.lower() in interest for keyword in search_keywords for interest in interests):
                        matching_members.append({
                            'username': member.username,
                            'full_name': member.full_name,
                            'skills': json.loads(member.skills),
                            'contact_info': json.loads(member.contact_info)
                        })
            
            return matching_members
        finally:
            session.close()

    async def format_user_info(self, user_info: dict) -> str:
        """Форматирует информацию о пользователе для вывода"""
        if not user_info:
            return ""
            
        formatted = []
        if user_info.get('full_name'):
            formatted.append(f"Имя: {user_info['full_name']}")
        if user_info.get('telegram_nick'):
            formatted.append(f"Telegram: @{user_info['telegram_nick']}")
        if user_info.get('occupation'):
            formatted.append(f"Специализация: {user_info['occupation']}")
        if user_info.get('skills'):
            skills = ', '.join(user_info['skills'])
            formatted.append(f"Навыки: {skills}")
        if user_info.get('company_info'):
            formatted.append(f"Компания: {user_info['company_info']}")
        about = user_info.get('about')
        if about and str(about).strip():
            formatted.append(f"О себе: {about}")
        if user_info.get('links'):
            links = [f"{v}" for v in user_info['links'].values()]
            if links:
                formatted.append(f"Ссылки: {', '.join(links)}")
                
        return '\n\n'.join(formatted)

    async def search_users_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Поиск пользователей по ключевому слову в специализации, навыках или описании"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT user_id, username, full_name, telegram_nick, 
                       occupation, skills, company_info, links
                FROM users
                WHERE occupation LIKE ? 
                   OR skills LIKE ? 
                   OR company_info LIKE ?
                   AND is_complete = TRUE
                """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
                
                users = []
                for row in cursor.fetchall():
                    user_info = {
                        'user_id': row[0],
                        'username': row[1],
                        'full_name': row[2],
                        'telegram_nick': row[3],
                        'occupation': row[4],
                        'skills': json.loads(row[5]) if row[5] else [],
                        'company_info': row[6],
                        'links': json.loads(row[7]) if row[7] else {}
                    }
                    users.append(user_info)
                return users
                
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователей по ключевому слову: {e}")
            return []

    async def clear_user_context(self, user_id: int) -> bool:
        """Очистка контекста диалога для конкретного пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Удаляем все сообщения из контекста
                cursor.execute("DELETE FROM message_context WHERE user_id = ?", (user_id,))
                
                # Удаляем все саммари
                cursor.execute("DELETE FROM chat_summaries WHERE user_id = ?", (user_id,))
                
                conn.commit()
                logger.info(f"✅ Контекст пользователя {user_id} успешно очищен")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке контекста пользователя {user_id}: {e}")
            return False

    async def get_context_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики контекста для пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                stats = {}
                
                # Общее количество сообщений
                cursor.execute(
                    "SELECT COUNT(*) FROM message_context WHERE user_id = ?",
                    (user_id,)
                )
                stats['total_messages'] = cursor.fetchone()[0]
                
                # Количество сообщений за последние 24 часа
                cursor.execute("""
                    SELECT COUNT(*) FROM message_context 
                    WHERE user_id = ? AND timestamp >= datetime('now', '-1 day')
                """, (user_id,))
                stats['messages_24h'] = cursor.fetchone()[0]
                
                # Количество саммари
                cursor.execute(
                    "SELECT COUNT(*) FROM chat_summaries WHERE user_id = ?",
                    (user_id,)
                )
                stats['summaries_count'] = cursor.fetchone()[0]
                
                # Последнее саммари
                cursor.execute("""
                    SELECT summary, created_at FROM chat_summaries 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC LIMIT 1
                """, (user_id,))
                last_summary = cursor.fetchone()
                if last_summary:
                    stats['last_summary'] = {
                        'text': last_summary[0][:100] + '...' if len(last_summary[0]) > 100 else last_summary[0],
                        'created_at': last_summary[1]
                    }
                
                # Размер активного контекста (последние 30 сообщений)
                cursor.execute("""
                    SELECT SUM(LENGTH(content)) FROM (
                        SELECT content FROM message_context 
                        WHERE user_id = ? 
                        ORDER BY timestamp DESC LIMIT 30
                    )
                """, (user_id,))
                stats['active_context_size'] = cursor.fetchone()[0] or 0
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики контекста для пользователя {user_id}: {e}")
            return None

    async def save_user_profile(self, user_id: int, profile_data: dict) -> bool:
        """Сохранение профиля пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существование пользователя
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Обновляем существующий профиль
                    query = """
                    UPDATE users SET 
                        full_name = ?,
                        telegram_nick = ?,
                        occupation = ?,
                        skills = ?,
                        company_info = ?,
                        links = ?,
                        about = ?,
                        last_active = CURRENT_TIMESTAMP,
                        is_complete = TRUE
                    WHERE user_id = ?
                    """
                    params = (
                        profile_data.get('full_name'),
                        profile_data.get('telegram_nick'),
                        profile_data.get('occupation'),
                        json.dumps(profile_data.get('skills', []), ensure_ascii=False),
                        profile_data.get('company_info'),
                        json.dumps(profile_data.get('links', {}), ensure_ascii=False),
                        profile_data.get('about'),
                        user_id
                    )
                else:
                    # Создаем новый профиль
                    query = """
                    INSERT INTO users (
                        user_id, full_name, telegram_nick, occupation,
                        skills, company_info, links, about, last_active, is_complete
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, TRUE)
                    """
                    params = (
                        user_id,
                        profile_data.get('full_name'),
                        profile_data.get('telegram_nick'),
                        profile_data.get('occupation'),
                        json.dumps(profile_data.get('skills', []), ensure_ascii=False),
                        profile_data.get('company_info'),
                        json.dumps(profile_data.get('links', {}), ensure_ascii=False),
                        profile_data.get('about')
                    )
                
                cursor.execute(query, params)
                conn.commit()
                logger.info(f"✅ Профиль пользователя {user_id} успешно сохранен")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении профиля пользователя {user_id}: {e}")
            return False

    async def search_users(self, query: str, search_type: str = 'all') -> List[Dict[str, Any]]:
        """
        Поиск пользователей по различным критериям
        search_type может быть: 'all', 'skills', 'occupation', 'name'
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                base_query = """
                SELECT user_id, full_name, telegram_nick, occupation,
                       skills, company_info, links, about
                FROM users
                WHERE is_complete = TRUE AND
                """
                
                if search_type == 'skills':
                    where_clause = "skills LIKE ?"
                    params = (f'%{query}%',)
                elif search_type == 'occupation':
                    where_clause = "occupation LIKE ?"
                    params = (f'%{query}%',)
                elif search_type == 'name':
                    where_clause = "full_name LIKE ?"
                    params = (f'%{query}%',)
                else:
                    # Поиск по всем полям
                    where_clause = """
                    (skills LIKE ? OR occupation LIKE ? OR 
                     full_name LIKE ? OR company_info LIKE ? OR about LIKE ?)
                    """
                    params = (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')
                
                cursor.execute(f"{base_query} {where_clause}", params)
                
                users = []
                for row in cursor.fetchall():
                    user_info = {
                        'user_id': row[0],
                        'full_name': row[1],
                        'telegram_nick': row[2],
                        'occupation': row[3],
                        'skills': json.loads(row[4]) if row[4] else [],
                        'company_info': row[5],
                        'links': json.loads(row[6]) if row[6] else {},
                        'about': row[7]
                    }
                    users.append(user_info)
                
                logger.info(f"🔍 Найдено {len(users)} пользователей по запросу '{query}' (тип: {search_type})")
                return users
                
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске пользователей: {e}")
            return []

    async def parse_registration_message(self, message_text: str) -> Optional[Dict[str, Any]]:
        """Парсинг сообщения регистрации в структурированные данные"""
        try:
            lines = message_text.split('\n')
            profile_data = {}
            
            for line in lines:
                if ':' not in line:
                    continue
                    
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'имя':
                    profile_data['full_name'] = value
                elif key == 'telegram':
                    profile_data['telegram_nick'] = value.lstrip('@')
                elif key == 'специализация':
                    profile_data['occupation'] = value
                elif key == 'навыки':
                    profile_data['skills'] = [s.strip() for s in value.split(',')]
                elif key == 'компания':
                    profile_data['company_info'] = value
                elif key == 'ссылки':
                    links = [link.strip() for link in value.split(',')]
                    profile_data['links'] = {f"link_{i+1}": link for i, link in enumerate(links)}
                elif key == 'о себе':
                    profile_data['about'] = value
            
            # Проверяем обязательные поля
            required_fields = ['full_name', 'telegram_nick', 'occupation', 'skills']
            if all(field in profile_data for field in required_fields):
                return profile_data
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге сообщения регистрации: {e}")
            return None

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получить всех пользователей из базы данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT user_id, username, full_name, telegram_nick, 
                       occupation, skills, company_info, links, about
                FROM users
                WHERE is_complete = TRUE
                """)
                
                users = []
                for row in cursor.fetchall():
                    user_info = {
                        'user_id': row[0],
                        'username': row[1],
                        'full_name': row[2],
                        'telegram_nick': row[3],
                        'occupation': row[4],
                        'skills': json.loads(row[5]) if row[5] else [],
                        'company_info': row[6],
                        'links': json.loads(row[7]) if row[7] else {},
                        'about': row[8]
                    }
                    users.append(user_info)
                
                logger.info(f"✅ Получено {len(users)} пользователей из базы данных")
                return users
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении списка пользователей: {e}")
            return []

    async def search_users_by_specialization(self, query: str) -> List[Dict[str, Any]]:
        """Получение всех пользователей из базы данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Простой запрос на получение всех пользователей
                query_sql = """
                SELECT user_id, username, full_name, telegram_nick, 
                       occupation, skills, company_info, links, about
                FROM users
                WHERE is_complete = TRUE
                """
                
                cursor.execute(query_sql)
                
                users = []
                for row in cursor.fetchall():
                    user_info = {
                        'user_id': row[0],
                        'username': row[1],
                        'full_name': row[2],
                        'telegram_nick': row[3],
                        'occupation': row[4],
                        'skills': json.loads(row[5]) if row[5] else [],
                        'company_info': row[6],
                        'links': json.loads(row[7]) if row[7] else {},
                        'about': row[8]
                    }
                    users.append(user_info)
                    logger.info(f"✅ Найден пользователь: {user_info['full_name']} ({user_info['occupation']})")
                    logger.info(f"   Навыки: {', '.join(user_info['skills'])}")
                
                logger.info(f"✅ Всего найдено пользователей: {len(users)}")
                return users
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении пользователей: {e}")
            return []

    async def update_system_prompt(self, prompt: str) -> bool:
        """Обновление системного промпта в базе данных"""
        return False

    async def get_system_prompt(self) -> str:
        """Получение актуального системного промпта из базы данных"""
        return None

    def get_context(self, user_id: int) -> list:
        """Получает контекст сообщений пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content FROM message_context 
                    WHERE user_id = ? 
                    ORDER BY timestamp ASC
                """, (user_id,))
                messages = cursor.fetchall()
                return [{"role": msg[0], "content": msg[1]} for msg in messages]
        except Exception as e:
            logger.error(f"Ошибка при получении контекста для пользователя {user_id}: {e}")
            return []

    def add_message_to_context(self, user_id: int, role: str, content: str):
        """Добавляет сообщение в контекст пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO message_context (user_id, role, content)
                    VALUES (?, ?, ?)
                """, (user_id, role, content))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении сообщения в контекст для пользователя {user_id}: {e}")
            return False

    def clear_context(self, user_id: int):
        """Очищает контекст сообщений пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM message_context WHERE user_id = ?", (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при очистке контекста для пользователя {user_id}: {e}")
            return False

    def get_system_prompt(self) -> str:
        """Получает системный промпт из базы данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = 'system_prompt'")
                result = cursor.fetchone()
                return result[0] if result else ""
        except Exception as e:
            logger.error(f"Ошибка при получении системного промпта: {e}")
            return ""

    def update_system_prompt(self, new_prompt: str):
        """Обновляет системный промпт в базе данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES ('system_prompt', ?, CURRENT_TIMESTAMP)
                """, (new_prompt,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении системного промпта: {e}")
            return False

    def get_all_summaries(self, user_id: int) -> list:
        """Получает все саммари пользователя по user_id, отсортированные по времени создания."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT summary, start_timestamp, end_timestamp, created_at
                    FROM chat_summaries
                    WHERE user_id = ?
                    ORDER BY created_at ASC
                    """,
                    (user_id,)
                )
                return [
                    {
                        'summary': row[0],
                        'start_timestamp': row[1],
                        'end_timestamp': row[2],
                        'created_at': row[3]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Ошибка при получении всех саммари пользователя {user_id}: {e}")
            return [] 