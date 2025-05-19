import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, Message, CallbackQuery, BotCommandScope
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ChatMemberHandler
import google.generativeai as genai
from google.generativeai import types
import re
import aiohttp
from database import Database
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import telegram
import replicate
import mimetypes
import tempfile
import io
import base64
import pathlib
import time
from collections import defaultdict
import sqlite3
from llm_provider import generate_response
import openai
import httpx

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ALLOWED_GROUP_ID = int(os.getenv('ALLOWED_GROUP_ID', '0'))
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Устанавливаем уровень логирования на DEBUG

# Инициализация Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')  # Основная модель для текста
vision_model = genai.GenerativeModel('gemini-pro-vision')  # Модель для работы с изображениями и документами

# Шаблоны для поиска
SEARCH_PATTERNS = [
    r"брат ищу (.*?)$"  # брат ищу разработчика, брат ищу маркетолога
]

# Шаблоны для поиска в сети
WEB_SEARCH_PATTERNS = [
    r"брат найди в сети (.*)",
    r"брат найди в интернете (.*)",
    r"брат поищи в сети (.*)",
    r"брат поищи в интернете (.*)",
    r"брат загугли (.*)"
]

# Шаблон для генерации фото
PHOTO_PATTERN = r"брат фото (.*?)$"

# Словарь соответствия различных вариаций специализаций
SPECIALIZATION_MAPPING = {
    'маркетинг': ['маркетинг', 'маркетолог', 'marketing', 'smm', 'контент', 'таргет', 'реклама'],
    'разработка': ['разработчик', 'программист', 'developer', 'кодер', 'backend', 'frontend'],
    'дизайн': ['дизайнер', 'designer', 'ui/ux', 'графический', 'веб-дизайн'],
    'продакт': ['продакт', 'product manager', 'product owner', 'менеджер продукта'],
    'проджект': ['project manager', 'проджект', 'менеджер проекта', 'пм']
}

# Системный промпт для бота
SYSTEM_PROMPT = """
Правила форматирования ответов:
1. Используй простые маркеры списка "•" вместо звездочек
2. Для выделения важного текста используй одинарные звездочки *текст*
3. Используй не более 2-3 эмодзи в ответе
4. Для курсива используй нижнее подчеркивание _текст_
5. Не используй такие заголовки и выделения со звздочками  *Кому он полезен?*    *SMM-Стратегия:*  
6. Не используй жирный шрифт 
7. Используй форматирование и разметку для Telegram


Ты Бот-брат, главный помощник и душа сообщества aitouch.ai. Твоя миссия — быть надежным другом и экспертом для каждого участника, помогая ориентироваться как в жизни сообщества, так и в возможностях нашего сервиса aitouch.ai.

Твои основные задачи:

Поддержка по Сообществу:

Помогать участникам находить нужных людей в сообществе для общения, сотрудничества или обмена опытом.
Предоставлять актуальную информацию о членах сообщества (в рамках допустимого и с уважением к приватности).
Направлять к правильным контактам, чатам или ресурсам по различным вопросам, возникающим внутри сообщества (мероприятия, правила, инициативы и т.д.).

Экспертиза по Сервису aitouch.ai:

Подробно рассказывать о сервисе aitouch.ai: объяснять, что это за инструмент, кому он будет полезен и как он помогает создавать профессиональный и эффективный контент, экономя время и повышая качество материалов.
Детально описывать функционал и возможности каждого инструмента сервиса, включая, но не ограничиваясь:

Aitouch.ai предлагает комплексный набор функций для оптимизации различных аспектов маркетинга и создания контента:

1. SMM-Стратегия:
Функция: Разработайте эффективную стратегию продвижения в социальных сетях, которая поможет вам увеличить охват, вовлеченность и продажи.
Настройка: Заполните информацию о вашем бизнесе (отрасль, целевая аудитория, цели). ИИ-помощник разработает стратегию продвижения с контент-планом и сценариями для постов и видео.

2. Box GPT:
Функция: Получите доступ к популярным нейросетям на русском языке без VPN.
Настройка: Выберите нейросеть (Chat GPT, Gemini, Claude, Coral, Groq, LLaMA) для решения различных задач: генерация текста, перевод, ответы на вопросы, и многое другое.

3. Art Box:
Функция: Создайте и редактируйте уникальные изображения с помощью искусственного интеллекта.
Настройка: Используйте технологии Midjourney, Recraft, Imagen, DALL-E, Flux, Artbox для генерации изображений по вашим промптам.

4. Промпт для генерации изображения:
Функция: Получите точный промпт, который поможет вам сгенерировать изображение, максимально соответствующее вашей идее.
Настройка: Опишите желаемое изображение, стиль, детали, и инструмент сгенерирует промпт для нейросети.

5. Заголовки для блога:
Функция: Напишите идеальный заголовок для статьи, поста в социальных сетях или видео, который привлечет внимание пользователей.
Настройка: Введите тему, ключевые слова, и инструмент сгенерирует несколько вариантов заголовков.

6. Генератор писем:
Функция: Получите эффективные тексты для email-рассылки или мессенджера, чтобы привлечь новых клиентов и удержать существующих.
Настройка: Выберите тип письма (например, приветственное, промо-письмо, письмо с предложением), укажите целевую аудиторию, и инструмент сгенерирует текст письма.

7. Генератор вакансии:
Функция: Создавайте привлекательные объявления о вакансиях, которые действительно заинтересуют будущих кандидатов.
Настройка: Введите название вакансии, описание обязанностей, требования к кандидатам, и инструмент сгенерирует текст объявления.

8. Генератор лид-магнитов:
Функция: Автоматизируйте создание текстов для привлечения клиентов: коммерческих предложений, гайдов или инструкций.
Настройка: Выберите тип лид-магнита, укажите целевую аудиторию, и инструмент сгенерирует текст.

9. Генератор статей:
Функция: Создавайте качественные тексты для коротких и длинных статей в пару кликов.
Настройка: Введите тему, ключевые слова, и инструмент сгенерирует текст статьи.

10. Рерайтер текстов:
Функция: Получите уникальные тексты на базе готовых материалов и статей.
Настройка: Загрузите текст, и инструмент перепишет его, сохраняя смысл, но меняя формулировки.

11. Идеи для блогов:
Функция: Получите идеи для новых постов в блоге, которые помогут вам увеличить трафик, лиды и продажи.
Настройка: Введите тему, ключевые слова, и инструмент сгенерирует список идей для постов.

12. Заголовки для рекламных объявлений:
Функция: Привлекайте внимание к рекламе с цепляющими и вовлекающими заголовками.
Настройка: Введите текст объявления, и инструмент сгенерирует несколько вариантов заголовков.

13. Описание для рекламных объявлений:
Функция: Автоматизируйте процесс создания текстов для рекламных объявлений и увеличьте конверсию ваших кампаний.
Настройка: Введите текст объявления, и инструмент сгенерирует описание, оптимизированное для привлечения внимания пользователей.

14. Описания для товаров:
Функция: Создавайте привлекательные описания товаров для вашего интернет-магазина или маркетплейса.
Настройка: Введите название товара, его характеристики, и инструмент сгенерирует описание, которое поможет вам увеличить продажи.

15. Описание компании и бренда:
Функция: Создайте текст о вашей компании, бренде или продукте - расскажите о себе рынку и привлеките новую аудиторию.
Настройка: Введите информацию о компании, и инструмент сгенерирует текст, который поможет вам представить себя потенциальным клиентам.

16. Лендинг:
Функция: Создайте тексты для лендинга с УТП продукта, его преимуществами и характеристиками, призывом к действию и ответами на вопросы.
Настройка: Введите информацию о продукте, и инструмент сгенерирует текст для лендинга.

17. Сценарии для коротких видео:
Функция: Создавайте уникальные сюжеты для своих видео в соц.сетях.
Настройка: Введите тему видео, и инструмент сгенерирует сценарий.

18. Генератор презентаций:
Функция: Создайте профессиональную презентацию по слайдам, с заголовками, ключевой идеей, выводами.
Настройка: Введите тему презентации, и инструмент сгенерирует структуру и текст слайдов.

19. Генератор сценариев для подкастов:
Функция: Создавайте сценарии для подкастов на основе предоставленных тем, формата подкаста и целевой аудитории.
Настройка: Введите тему подкаста, и инструмент сгенерирует сценарий.

20. Планирование контент-календаря:
Функция: Создайте контент-календарь с рекомендациями по публикациям, срокам и темам, основываясь на целевых метриках.
Настройка: Введите информацию о вашем бизнесе, и инструмент сгенерирует контент-календарь.

21. Генератор описаний для видео:
Функция: Создайте оптимизированные и привлекательные описания для видео на YouTube и других платформах.
Настройка: Введите информацию о видео, и инструмент сгенерирует описание.

22. Создание сценариев для вебинаров:
Функция: Получите детализированные сценарии на основе темы вебинара, целевой аудитории и целей мероприятия.
Настройка: Введите информацию о вебинаре, и инструмент сгенерирует сценарий.

23. Создание кейсов:
Функция: Создайте детализированный кейс с анализом ситуации, шагами решения и результатами.
Настройка: Введите информацию о кейсе, и инструмент сгенерирует текст.

24. Генератор контента для образовательных программ:
Функция: Получите готовый контент, который поможет обучать сотрудников или клиентов продуктам и услугам.
Настройка: Введите информацию об образовательной программе, и инструмент сгенерирует контент.

Обучающие видео:

- Краткий обзор сервиса AiTouch
Познакомьтесь с AITouch: навигация по сайту, основные функции и инструменты для быстрого старта.

- GPT Box и обзор языковых моделей
Обзор возможностей GPT Box, языковых моделей, о системе токенов и создании эффективных промптов для общения с нейросетью.

- Art Box и создание изображений
Создание уникальных изображений с Art Box: структура эффективного промпта, Face Swap и Photomaker.

- Обзор инструментов для отдельных задач
Обзор 8 новых инструментов AITouch, а также решения для текста и e-commerce задач.

- Идеи и контент для блогов
Создание идей, заголовков, постов и визуального контента для блогов с помощью GPT Box и Art Box.

- GPT и Art Box для статей и других текстов
Ускорение написания статей с GPT Box, их преобразование и создание уникальных иллюстраций для текстовых материалов.

- Концепции и креативный контент с AITouch
Создание креативных концепций с GPT Box, Art Box и другими инструментами. Генерация JTBD, УТП и карточки товара.

- Комплексное создание контент-плана
Создание контент-плана: идеи для постов, визуальные примеры и упаковка всего в удобный формат таблиц для работы.

Общий Стиль Взаимодействия:

Всегда быть дружелюбным, отзывчивым, терпеливым и максимально полезным.
Обращаться к пользователям уважительно и "по-братски" – создавай атмосферу поддержки и взаимопомощи, как в настоящем братстве.
Если не знаешь ответа на какой-то специфический вопрос, честно скажи об этом и постарайся направить пользователя к тому, кто может помочь.
Твоя цель – сделать пребывание в сообществе aitouch.ai максимально комфортным, продуктивным и интересным для каждого участника. Будь проактивным, предлагай помощь и делись знаниями!

Старайся отвечать не сильно длинными сообщениями. 

Обращайся к пользователям уважительно и по-братски.

Когда рекомендуешь в сооществе tothom из нашей базы то всегда выводи его никнейм и ссылку на его профиль в телеграм @
"""

def format_response(text: str) -> str:
    """Форматирование ответа для корректного отображения в Telegram"""
    # Удаляем Markdown-разметку
    text = re.sub(r'[*_`#]', '', text)
    
    # Удаляем ссылки в квадратных скобках
    text = re.sub(r'\[\d+\]', '', text)
    
    # Заменяем заголовки на обычный текст
    text = re.sub(r'^###\s*', '📌 ', text, flags=re.MULTILINE)
    
    # Удаляем все звездочки в начале строк
    text = re.sub(r'^\*+\s*', '• ', text, flags=re.MULTILINE)
    
    # Заменяем маркеры списка на точки
    text = re.sub(r'^\s*[-•*]\s+', '• ', text, flags=re.MULTILINE)
    
    # Разбиваем текст на параграфы
    paragraphs = text.split('\n')
    formatted_paragraphs = []
    
    # Флаг для отслеживания списков
    in_list = False
    
    for i, paragraph in enumerate(paragraphs):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # Определяем, является ли строка элементом списка
        is_list_item = paragraph.startswith('•')
        
        # Добавляем дополнительный отступ перед новым списком
        if is_list_item and not in_list and formatted_paragraphs:
            formatted_paragraphs.append('')
            
        # Добавляем отступ после приветствия
        if '👋' in paragraph:
            formatted_paragraphs.append(paragraph)
            formatted_paragraphs.append('')
            continue
            
        # Добавляем отступ перед новым смысловым блоком
        if ':' in paragraph and not is_list_item:
            if formatted_paragraphs:
                formatted_paragraphs.append('')
            formatted_paragraphs.append(paragraph)
            formatted_paragraphs.append('')
            continue
            
        # Обработка элементов списка
        if is_list_item:
            in_list = True
            formatted_paragraphs.append(paragraph)
        else:
            if in_list:
                formatted_paragraphs.append('')
                in_list = False
            formatted_paragraphs.append(paragraph)
            
    # Собираем текст обратно
    result = '\n'.join(formatted_paragraphs)
    
    # Удаляем множественные пустые строки
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
    
    return result.strip()

class PerplexityAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY не установлен в переменных окружения")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
    async def search(self, query):
        if not query:
            raise ValueError("Поисковый запрос не может быть пустым")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": """Ты помощник, который ищет информацию в интернете. 
                    Следуй этим правилам при ответе:
                    1. Отвечай на русском языке
                    2. Структурируй информацию по пунктам
                    3. Используй короткие, информативные параграфы
                    4. Выделяй важные моменты в отдельные пункты
                    5. Добавляй заголовки к разным частям ответа
                    6. Пиши кратко и по существу
                    7. Если есть числа, даты или цены - выноси их отдельно
                    8. Избегай длинных, сложных предложений
                    9. Не используй специальные символы разметки (* _ # и т.д.)"""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result['choices'][0]['message']['content']
                        # Очищаем текст от специальных символов разметки
                        response_text = re.sub(r'[*_#`]', '', response_text)
                        return response_text
                    else:
                        error_text = await response.text()
                        logger.error(f"Perplexity API error: Status {response.status}, Response: {error_text}")
                        raise Exception(f"Ошибка API: {response.status}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error during Perplexity API request: {e}")
            raise Exception("Ошибка сети при запросе к API")
        except Exception as e:
            logger.error(f"Unexpected error during Perplexity search: {e}")
            raise

class ConversationContext:
    def __init__(self, db):
        self.db = db  # SQLite database
        self.contexts = {}  # Кэш для активных контекстов
        self.max_context_length = 10
        self.max_tokens = 2000
        
    async def add_message(self, user_id: int, role: str, content: str):
        """Добавить сообщение в контекст пользователя"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.contexts[user_id] = self.contexts.get(user_id, []) + [message]
        
        if len(self.contexts[user_id]) > self.max_context_length:
            await self._summarize_context(user_id)
    
    async def _summarize_context(self, user_id: int):
        """Сжать контекст, создав краткое содержание предыдущих сообщений"""
        try:
            logger.info(f"🔄 Начинаю суммаризацию контекста для пользователя {user_id}")
            
            # Получаем текущий контекст из базы данных
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content, timestamp 
                    FROM message_context 
                    WHERE user_id = ? 
                    ORDER BY timestamp ASC
                """, (user_id,))
                messages = cursor.fetchall()
                
            if not messages:
                logger.info("❌ Контекст пуст, нечего суммаризировать")
                return
                
            logger.info(f"📊 Текущая длина контекста: {len(messages)} сообщений")
            
            # Формируем промпт для сжатия контекста
            summary_prompt = "Сделай краткую выжимку из этого диалога, сохранив ключевые моменты и важные детали:\n\n"
            messages_to_summarize = messages[:-5]  # Оставляем последние 5 сообщений
            logger.info(f"📝 Суммаризирую {len(messages_to_summarize)} сообщений, оставляю последние 5")
            
            for role, content, _ in messages_to_summarize:
                summary_prompt += f"{role}: {content}\n"
                
            try:
                logger.info("🤖 Отправляю запрос на суммаризацию в Gemini")
                response = model.generate_content(summary_prompt)
                summary = response.text
                logger.info(f"✅ Получен ответ от Gemini, длина саммари: {len(summary)} символов")
                
                # Сохраняем саммари в базу данных
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO chat_summaries (user_id, summary, created_at)
                        VALUES (?, ?, datetime('now'))
                    """, (user_id, summary))
                    conn.commit()
                    logger.info("✅ Саммари успешно сохранено в базу данных")
                    
                    # Обновляем контекст: удаляем старые сообщения и добавляем саммари
                    cursor.execute("DELETE FROM message_context WHERE user_id = ? AND timestamp < ?", 
                                 (user_id, messages[-5][2]))  # Оставляем только последние 5 сообщений
                    
                    # Добавляем саммари как системное сообщение
                    cursor.execute("""
                        INSERT INTO message_context (user_id, role, content, timestamp)
                        VALUES (?, 'system', ?, datetime('now'))
                    """, (user_id, f"Краткое содержание предыдущего диалога:\n{summary}"))
                    conn.commit()
                    
                logger.info("✅ Контекст успешно обновлен")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при суммаризации контекста: {str(e)}")
                # В случае ошибки оставляем только последние 5 сообщений
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM message_context WHERE user_id = ? AND timestamp < ?", 
                                 (user_id, messages[-5][2]))
                    conn.commit()
                logger.info("⚠️ Оставлены только последние 5 сообщений из-за ошибки")
                
        except Exception as e:
            logger.error(f"❌ Ошибка в методе _summarize_context: {str(e)}")
            return
    
    async def get_context(self, user_id: int, days_back: int = None) -> list:
        """Получить контекст пользователя с возможностью указать глубину поиска"""
        await self.load_context(user_id)
        
        if not days_back:
            return self.contexts.get(user_id, [])
            
        # Если указано количество дней, добавляем архивные сообщения
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Получаем архивные записи
        # archive_cursor = self.db.context_archive.find({
        #     "user_id": user_id,
        #     "archived_at": {"$gte": cutoff_date}
        # }).sort("archived_at", -1)
        
        # archived_messages = []
        # async for doc in archive_cursor:
        #     archived_messages.extend(doc["messages"])
        
        # Объединяем с текущим контекстом
        current_context = self.contexts.get(user_id, [])
        all_messages = current_context  # Только локальный контекст
        
        # Фильтруем по дате
        filtered_messages = [
            msg for msg in all_messages
            if datetime.fromisoformat(msg["timestamp"]) >= cutoff_date
        ]
        
        return filtered_messages
    
    async def clear_context(self, user_id: int):
        """Очистить контекст пользователя"""
        if user_id in self.contexts:
            del self.contexts[user_id]
        # await self.db.contexts.delete_one({"user_id": user_id})
        
    async def cleanup_old_contexts(self, days: int = 30):
        """Очистить старые контексты"""
        # cutoff_date = datetime.now() - timedelta(days=days)
        # await self.db.contexts.delete_many({
        #     "last_updated": {"$lt": cutoff_date}
        # })
        pass

class ImageGenerator:
    def __init__(self, api_token):
        self.client = replicate.Client(api_token=api_token)
        self.model_version = "black-forest-labs/flux-schnell"

    async def translate_prompt(self, prompt: str) -> str:
        """Переводит промпт на английский и добавляет улучшающие модификаторы через OpenAI только через прокси"""
        try:
            system_prompt = (
                "Переведи текст на английский и добавь модификаторы. Верни ТОЛЬКО финальный промпт без объяснений. "
                "Добавь в конец: high quality, detailed, sharp focus, professional photography, cinematic lighting, masterpiece, best quality"
            )
            openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            enhanced_prompt = response.choices[0].message.content.strip()
            enhanced_prompt = re.sub(r'\s+', ' ', enhanced_prompt)
            enhanced_prompt = re.sub(r'[\*\[\]#]', '', enhanced_prompt)
            logger.info(f"🔄 Промпт переведен и улучшен (OpenAI): {enhanced_prompt}")
            return enhanced_prompt
        except Exception as e:
            logger.error(f"❌ Ошибка при переводе промпта через OpenAI: {e}")
            return f"{prompt}, high quality, detailed, sharp focus, professional photography, cinematic lighting, masterpiece, best quality"
    
    async def generate_image(self, prompt: str) -> str:
        """Генерирует изображение используя Replicate API"""
        try:
            # Переводим и улучшаем промпт
            enhanced_prompt = await self.translate_prompt(prompt)
            
            # Параметры для генерации
            params = {
                "prompt": enhanced_prompt,
                "go_fast": True,
                "megapixels": "1",
                "num_outputs": 1,
                "aspect_ratio": "1:1",
                "output_format": "jpg",
                "output_quality": 80,
                "num_inference_steps": 4
            }
            
            logger.info(f"🎨 Отправляем запрос на генерацию с параметрами: {params}")
            
            # Создаем предсказание используя replicate.run()
            output = replicate.run(
                self.model_version,
                input=params
            )
            
            # Получаем URL изображения
            if output:
                # Для flux-schnell output это список, берем первый элемент
                image_data = next(iter(output))
                image_url = str(image_data)
                logger.info(f"✅ Изображение успешно сгенерировано: {image_url}")
                return image_url
            else:
                raise Exception("Пустой результат генерации")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации изображения: {e}")
            raise

class FileHandler:
    def __init__(self, model):
        self.model = model
        self.max_file_size = 20 * 1024 * 1024  # 20 MB
        self.mime_types = {
            'application/pdf': 'PDF',
            'application/msword': 'DOC',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
            'text/plain': 'TXT',
            'image/jpeg': 'JPEG',
            'image/png': 'PNG',
            'video/mp4': 'MP4',
            'audio/mpeg': 'MP3',
            'audio/wav': 'WAV'
        }
        self.logger = logging.getLogger(__name__)

    async def process_file(self, file_data: bytes, file_name: str, mime_type: str, user_prompt: str = None) -> Tuple[bool, str]:
        """Обработка файла через Gemini API"""
        try:
            self.logger.info(f"🔄 Начинаю обработку файла: {file_name} (тип: {mime_type})")
            
            # Проверяем размер файла
            file_size = len(file_data)
            if file_size > self.max_file_size:
                return False, "Файл слишком большой. Максимальный размер: 20 МБ"

            # Проверяем тип файла
            if mime_type not in self.mime_types:
                return False, "Неподдерживаемый тип файла"

            # Кодируем файл в base64
            file_base64 = base64.b64encode(file_data).decode('utf-8')

            # Формируем промпт в зависимости от типа файла
            if 'image' in mime_type:
                prompt = f"Опиши подробно, что изображено на этой картинке. {user_prompt if user_prompt else ''}"
            elif 'video' in mime_type:
                prompt = f"Опиши подробно содержание этого видео. {user_prompt if user_prompt else ''}"
            elif 'audio' in mime_type:
                prompt = f"Опиши подробно содержание этой аудиозаписи. {user_prompt if user_prompt else ''}"
            else:
                prompt = f"Проанализируй и сделай подробное резюме этого документа. {user_prompt if user_prompt else ''}"

            # Создаем запрос для Gemini
            request = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": file_base64
                            }
                        }
                    ]
                }]
            }

            # Отправляем запрос
            response = self.model.generate_content(**request)
            
            if response and response.text:
                return True, response.text
            else:
                return False, "Не удалось обработать файл"

        except Exception as e:
            self.logger.error(f"❌ Ошибка при обработке файла: {str(e)}", exc_info=True)
            return False, f"Произошла ошибка при обработке файла: {str(e)}"

class RateLimiter:
    def __init__(self):
        # Ограничения по количеству запросов в минуту для пользователя
        self.user_limits = defaultdict(lambda: {
            'requests': 0,
            'last_reset': time.time(),
            'blocked_until': None
        })
        
        # Ограничения для группы
        self.group_limits = defaultdict(lambda: {
            'requests': 0,
            'last_reset': time.time()
        })
        
        # Настройки лимитов
        self.MAX_REQUESTS_PER_MINUTE = 30  # Максимум запросов в минуту для пользователя
        self.GROUP_MAX_REQUESTS_PER_MINUTE = 100  # Максимум запросов в минуту для группы
        self.BLOCK_DURATION = 300  # Длительность блокировки в секундах (5 минут)
        self.RESET_INTERVAL = 60  # Интервал сброса счетчиков в секундах
        
        # Список заблокированных пользователей
        self.blocked_users = set()
        
    def _reset_counters(self, user_id: int, chat_id: int):
        """Сброс счетчиков если прошел интервал"""
        current_time = time.time()
        
        # Сброс пользовательских счетчиков
        if current_time - self.user_limits[user_id]['last_reset'] >= self.RESET_INTERVAL:
            self.user_limits[user_id]['requests'] = 0
            self.user_limits[user_id]['last_reset'] = current_time
            
        # Сброс групповых счетчиков
        if current_time - self.group_limits[chat_id]['last_reset'] >= self.RESET_INTERVAL:
            self.group_limits[chat_id]['requests'] = 0
            self.group_limits[chat_id]['last_reset'] = current_time
            
    def is_allowed(self, user_id: int, chat_id: int) -> tuple[bool, str]:
        """Проверка возможности обработки запроса"""
        self._reset_counters(user_id, chat_id)
        
        # Проверка блокировки пользователя
        if user_id in self.blocked_users:
            blocked_until = self.user_limits[user_id]['blocked_until']
            if blocked_until and time.time() < blocked_until:
                remaining = int(blocked_until - time.time())
                return False, f"Вы временно заблокированы. Осталось {remaining} секунд."
            else:
                self.blocked_users.remove(user_id)
        
        # Проверка лимитов пользователя
        user_requests = self.user_limits[user_id]['requests']
        if user_requests >= self.MAX_REQUESTS_PER_MINUTE:
            self.blocked_users.add(user_id)
            self.user_limits[user_id]['blocked_until'] = time.time() + self.BLOCK_DURATION
            return False, f"Превышен лимит запросов. Блокировка на {self.BLOCK_DURATION} секунд."
            
        # Проверка лимитов группы
        group_requests = self.group_limits[chat_id]['requests']
        if group_requests >= self.GROUP_MAX_REQUESTS_PER_MINUTE:
            return False, "Превышен групповой лимит запросов. Попробуйте позже."
            
        # Увеличение счетчиков
        self.user_limits[user_id]['requests'] += 1
        self.group_limits[chat_id]['requests'] += 1
        
        return True, ""
        
    async def log_suspicious_activity(self, user_id: int, chat_id: int, message: str):
        """Логирование подозрительной активности"""
        logger.warning(
            f"🚨 Подозрительная активность!\n"
            f"Пользователь: {user_id}\n"
            f"Чат: {chat_id}\n"
            f"Сообщение: {message}\n"
            f"Время: {datetime.now()}"
        )

class BratBot:
    def __init__(self):
        self.allowed_group_id = ALLOWED_GROUP_ID
        self.db = Database()
        self.system_prompt = SYSTEM_PROMPT
        self.perplexity = None
        self.image_generator = None
        self.file_handler = None
        self.rate_limiter = RateLimiter()
        self.waiting_for_profile = {}  # user_id: {'mode': 'register'/'update', 'msg_id': ...}
        
    async def setup(self, application: Application = None):
        """Инициализация компонентов бота"""
        try:
            logger.info("Начинаю инициализацию бота...")
            
            # Загружаем актуальный системный промпт
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = 'system_prompt'")
                row = cursor.fetchone()
                if row:
                    self.system_prompt = row[0]
                    logger.info("✅ Загружен актуальный системный промпт из базы данных")
                else:
                    # Сохраняем начальный системный промпт
                    cursor.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?)",
                        ('system_prompt', self.system_prompt)
                    )
                    conn.commit()
                    logger.info("✅ Создан начальный системный промпт")

            # Инициализация Perplexity API
            perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
            if perplexity_api_key:
                try:
                    self.perplexity = PerplexityAPI(perplexity_api_key)
                    logger.info("Perplexity API успешно инициализирован")
                except Exception as e:
                    logger.error(f"❌ Ошибка инициализации Perplexity API: {e}")
                    self.perplexity = None
            else:
                self.perplexity = None
                logger.warning("Perplexity API отключен из-за отсутствия ключа API")

            # Инициализация Image Generator
            if REPLICATE_API_TOKEN:
                try:
                    self.image_generator = ImageGenerator(REPLICATE_API_TOKEN)
                    logger.info("Image Generator успешно инициализирован")
                except Exception as e:
                    logger.error(f"❌ Ошибка инициализации Image Generator: {e}")
                    self.image_generator = None
            else:
                self.image_generator = None
                logger.warning("Image Generator отключен из-за отсутствия ключа API")

            # Инициализация FileHandler
            try:
                self.file_handler = FileHandler(model)
                logger.info("✅ FileHandler успешно инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации FileHandler: {e}")
                self.file_handler = None

            # Настройка команд бота если есть application
            if application:
                await self.setup_commands(application)
                logger.info("Команды бота настроены")

            logger.info("✅ Инициализация бота завершена")

        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации компонентов: {e}")
            raise

    async def check_access(self, update: Update) -> bool:
        """Проверка доступа к боту"""
        if not update.effective_chat:
            logger.warning(f"Попытка доступа без контекста чата")
            return False
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else None
        
        logger.debug(f"Проверка доступа: chat_id={chat_id}, allowed_group_id={self.allowed_group_id}, user_id={user_id}")
        
        if chat_id != self.allowed_group_id:
            logger.warning(
                f"Попытка несанкционированного доступа: chat_id={chat_id}, "
                f"user_id={user_id}, chat_type={update.effective_chat.type}"
            )
            await update.message.reply_text(
                "⚠️ Извините, я работаю только в определенной группе. "
                "Пожалуйста, обратитесь к администратору для получения доступа."
            )
            return False
        
        logger.debug(f"Доступ разрешен для chat_id={chat_id}, user_id={user_id}")
        return True

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        if not await self.check_access(update):
            return

        await update.message.reply_text(
            "Привет! Я Бот-брат, помощник сообщества.\n"
            "Чтобы получить помощь, напишите сообщение в группе, я постараюсь помочь!\n"
            "Также доступны команды:\n"
            "/help - показать справку\n"
            "/info - информация о сообществе"
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        if not await self.check_access(update):
            return

        is_admin = await self.is_admin(update)
        
        help_text = (
            "👋 Привет! Я Бот-брат, помощник сообщества aitouch.ai\n\n"
            "🤝 Основные команды:\n"
            "• /help - эта справка\n"
            "• /info - информация о боте\n"
            "• /register - зарегистрироваться в сообществе\n"
            "• /update_profile - обновить свой профиль\n"
            "• /members - показать всех участников сообщества\n\n"
        )

       
        help_text += (
            "🔍 Поиск участников:\n"
            "• брат ищу [специализация] - поиск участников по специализации\n"
            "Например: 'брат ищу разработчика' или 'брат ищу маркетолога'\n\n"
            "🌐 Поиск в интернете:\n"
            "• брат найди в сети [запрос]\n"
            "• брат найди в интернете [запрос]\n"
            "• брат поищи в сети [запрос]\n"
            "• брат поищи в интернете [запрос]\n"
            "• брат загугли [запрос]\n"
            "Например: 'брат найди в сети погода в москве'\n\n"
            "🏞 Генерация изображений:\n"
            "• брат фото [запрос] — сгенерировать изображение по описанию\n"
            "Например: 'брат фото красивая черная кошка'\n\n"
            "💬 Общение с ботом:\n"
            "• Начните сообщение со слова 'брат' или обратитесь ко мне @AiBratBot\n"
            "• Можете задавать любые вопросы о сервисе aitouch.ai\n"
            "• Спрашивайте совета или помощи в решении задач\n\n"
            "📝 Регистрация в сообществе:\n"
            "1. Используйте команду /register\n"
            "2. Заполните форму с информацией о себе\n"
            "3. Обновляйте информацию командой /update_profile\n\n"
            "🤝 Я всегда готов помочь! Не стесняйтесь обращаться с любыми вопросами."
        )
        await update.message.reply_text(help_text)

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /info"""
        if not await self.check_access(update):
            return

        info_text = (
            "ℹ️ О боте:\n\n"
            "Я - бот-помощник, который использует искусственный интеллект для общения и помощи.\n"
            "Работаю на базе нескольких нейросетей.\n\n"
            "Основные возможности:\n"
            "• Ответы на вопросы\n"
            "• Поиск информации\n"
            "• Создание фото\n"
            "• Помощь с задачами\n"
            "• Рассказ о сервисе aitouch.ai\n"
            "• Общение на разные темы\n\n"
            "🔍 История общения сохраняется и вы всегда можете найти нужную информацию, спросив:\n"
            "• что мы обсуждали про [тема]\n"
            "• найди в истории про [тема]\n"
            "• расскажи обо мне "
        )
        await update.message.reply_text(info_text)

    async def get_model_response(self, messages: list, user_id: int) -> str:
        try:
            logger.info(f"📝 Начинаю обработку контекста из {len(messages)} сообщений для user_id={user_id}")
            # Получаем все саммари пользователя
            all_summaries = []
            if user_id:
                all_summaries = self.db.get_all_summaries(user_id)
            # Определяем, нужно ли создать новое саммари
            block_size = 30
            last_summarized_idx = 0
            last_end = None
            if all_summaries:
                last_end = all_summaries[-1]['end_timestamp']
                # last_end может быть None, если в базе что-то не так
                for i, msg in enumerate(messages):
                    msg_ts = msg.get('timestamp')
                    if last_end and msg_ts and msg_ts > last_end:
                        last_summarized_idx = i
                        break
            unsummarized = messages[last_summarized_idx: -10 if len(messages) > 10 else None]
            if len(unsummarized) >= block_size:
                logger.info(f"🟡 Новый блок для саммаризации: {len(unsummarized)} сообщений")
                # Новый смысловой промпт для саммари:
                summary_prompt = (
                    "Прочитай диалог ниже и сделай краткое смысловое описание: \n"
                    "- О чём спрашивал пользователь?\n"
                    "- Какие задачи или вопросы поднимались?\n"
                    "- Какие ответы и советы дал ассистент?\n"
                    "- Не пересказывай всё подряд, выдели только суть и ключевые моменты, без лишних деталей.\n"
                    "- Не копируй текст сообщений, а именно опиши, что происходило.\n\n"
                )
                for msg in unsummarized:
                    role = "Пользователь" if msg["role"] == "user" else "Ассистент"
                    summary_prompt += f"{role}: {msg['content']}\n"
                logger.info(f"[SUMMARIZATION] Промпт для саммаризации ({len(summary_prompt)} символов):\n{summary_prompt[:300]}...\n[...]")
                # Используем ту же модель, что и для обычных ответов:
                summary = generate_response(unsummarized, summary_prompt)
                logger.info(f"[SUMMARIZATION] Саммари ({len(summary)} символов):\n{summary[:300]}...\n[...]")
                await self.db.create_chat_summary(user_id, summary)
                all_summaries = self.db.get_all_summaries(user_id)
            else:
                if all_summaries:
                    logger.info(f"[PROMPT] Нет новых блоков для саммаризации. Используются саммари: {[i+1 for i in range(len(all_summaries))]}")
                else:
                    logger.info(f"[PROMPT] Нет саммари, используется только история сообщений.")
            prompt = self.system_prompt + "\n\n"
            for idx, summ in enumerate(all_summaries):
                prompt += f"[Краткое содержание блока {idx+1}]\n{summ['summary']}\n\n"
            last_msgs = messages[-10:] if len(messages) > 10 else messages
            prompt += "[Последние сообщения]\n"
            for msg in last_msgs:
                role = "Пользователь" if msg["role"] == "user" else "Ассистент"
                prompt += f"{role}: {msg['content']}\n"
            logger.info(f"[LLM] Итоговый промпт ({len(prompt)} символов):\n{prompt}")
            response = generate_response([], prompt)
            formatted_response = format_response(response)
            logger.info(f"📥 Получен ответ от модели (длина: {len(formatted_response)} символов)")
            return formatted_response
        except Exception as e:
            logger.error(f"❌ Ошибка при получении ответа от LLM: {str(e)}")
            raise

    async def register(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Инструкция по созданию профиля через 'брат профиль'"""
        # Удаляем приветственное сообщение, если оно есть
        welcome_msg_id = context.chat_data.get('welcome_msg_id')
        if welcome_msg_id:
            try:
                await update.message.bot.delete_message(chat_id=update.effective_chat.id, message_id=welcome_msg_id)
            except Exception:
                pass
            context.chat_data['welcome_msg_id'] = None
        instruction = (
            "Для того чтобы создать профиль в сообществе, напишите в чат:\n\n"
            "```\n"
            "брат профиль\n"
            "Имя: Ваше полное имя\n"
            "Telegram: @ваш_ник\n"
            "Специализация: Ваша специализация\n"
            "Навыки: Навык1, Навык2, Навык3\n"
            "Компания: Название компании (если есть)\n"
            "О себе: Краткое описание\n"
            "Ссылки: ссылка1, ссылка2\n"
            "```\n\n"
            "Бот добавит вас в базу нашего сообщества."
        )
        await update.message.reply_text(instruction, parse_mode='Markdown')

    async def update_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /update_profile"""
        if not await self.check_access(update):
            return
        user_id = update.effective_user.id
        user_info = await self.db.get_user_info(user_id)
        if not user_info:
            await update.message.reply_text(
                "У вас еще нет профиля. Используйте команду /register для создания профиля.",
                parse_mode=None
            )
            return
        current_info = await self.db.format_user_info(user_info)
        update_form = (
            f"Ваш текущий профиль:\n\n{current_info}\n\n"
            "Для обновления данных отправьте команду в чат в формате:\n\n"
            "```\n"
            "брат профиль\n"
            "Имя: Ваше полное имя\n"
            "Telegram: @ваш_ник\n"
            "Специализация: Ваша специализация\n"
            "Навыки: Навык1, Навык2, Навык3\n"
            "Компания: Название компании (если есть)\n"
            "О себе: Краткое описание\n"
            "Ссылки: ссылка1, ссылка2\n"
            "```\n\n"
            "Бот сохранит данные в профиль."
        )
        msg = await update.message.reply_text(update_form, parse_mode='Markdown')
        self.waiting_for_profile[user_id] = {'mode': 'update', 'msg_id': msg.message_id}

    async def handle_registration_or_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ответа пользователя для регистрации или обновления профиля"""
        user_id = update.effective_user.id
        text = update.message.text
        wait = self.waiting_for_profile.get(user_id)
        if not wait:
            return
        # Проверяем, что это reply на сообщение бота с формой
        if not update.message.reply_to_message or update.message.reply_to_message.message_id != wait['msg_id']:
            return
        is_registration = wait['mode'] == 'register'
        is_update = wait['mode'] == 'update'
        # Парсим данные
        profile_data = await self.db.parse_registration_message(text)
        if not profile_data:
            await update.message.reply_text(
                "❌ Не удалось распознать данные. Пожалуйста, используйте предложенный формат."
            )
            return
        # Для обновления профиля — обновляем только указанные поля
        if is_update:
            user_info = await self.db.get_user_info(user_id)
            for key in user_info:
                if key not in profile_data:
                    profile_data[key] = user_info[key]
        # Сохраняем профиль
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                exists = cursor.fetchone()
                if exists:
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
            # Очищаем ожидание только после успешного сохранения
            if user_id in self.waiting_for_profile:
                del self.waiting_for_profile[user_id]
            # Обновляем системный промпт
            await self.update_prompt_with_users()
            await update.message.reply_text("✅ Профиль успешно сохранён!")
        except Exception as e:
            logger.error(f"Ошибка при сохранении профиля: {e}")
            await update.message.reply_text("❌ Произошла ошибка при сохранении профиля. Попробуйте позже.")

    async def update_prompt_with_users(self):
        """Обновляет системный промпт с учётом всех пользователей"""
        try:
            user_lines = []
            for full_name, occupation, skills_json, telegram_nick in [
                (row[0], row[1], row[2], row[3])
                for row in self.db.get_connection().cursor().execute(
                    "SELECT full_name, occupation, skills, telegram_nick FROM users WHERE is_complete = TRUE"
                )
            ]:
                skills = ', '.join(json.loads(skills_json)) if skills_json else ''
                line = f"• {full_name} — {occupation} ({skills})"
                if telegram_nick:
                    if not telegram_nick.startswith('@'):
                        telegram_nick = '@' + telegram_nick
                    line += f" {telegram_nick}"
                user_lines.append(line)
            users_block = '\n'.join(user_lines)
            new_prompt = SYSTEM_PROMPT + "\n\nВ сообществе зарегистрированы:\n" + users_block
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES ('system_prompt', ?, datetime('now'))
                """, (new_prompt,))
                conn.commit()
            self.system_prompt = new_prompt
            logger.info("Системный промпт обновлён с учётом пользователей")
        except Exception as e:
            logger.error(f"Ошибка при обновлении промпта с пользователями: {e}")

    async def members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список всех участников сообщества"""
        if not await self.check_access(update):
            return

        try:
            # Получаем всех пользователей из базы данных
            users = await self.db.get_all_users()

            if not users:
                await update.message.reply_text("В сообществе пока нет зарегистрированных участников.")
                return

            # Формируем сообщение со списком участников
            message = "📋 <b>Участники сообщества:</b>\n\n"
            for user in users:
                message += f"👤 <b>Имя:</b> {user.get('full_name', '—')}\n"
                message += f"📝 <b>О себе:</b> {user.get('about', '—')}\n"
                message += f"💼 <b>Специализация:</b> {user.get('occupation', '—')}\n"
                if user.get('skills'):
                    message += f"🛠 <b>Навыки:</b> {', '.join(user['skills'])}\n"
                else:
                    message += f"🛠 <b>Навыки:</b> —\n"
                # Telegram ник с @
                telegram_nick = user.get('telegram_nick')
                if telegram_nick:
                    if not telegram_nick.startswith('@'):
                        telegram_nick = '@' + telegram_nick
                    message += f"📱 <b>Telegram:</b> {telegram_nick}\n"
                else:
                    message += f"📱 <b>Telegram:</b> —\n"
                # Ссылки
                links = user.get('links')
                if links:
                    if isinstance(links, dict):
                        links_str = ', '.join([str(v) for v in links.values()])
                    elif isinstance(links, list):
                        links_str = ', '.join(links)
                    else:
                        links_str = str(links)
                    message += f"🔗 <b>Ссылки:</b> {links_str}\n"
                else:
                    message += f"🔗 <b>Ссылки:</b> —\n"
                message += "\n"

            # Разбиваем на части, если сообщение слишком длинное
            if len(message) > 4096:
                parts = [message[i:i+4096] for i in range(0, len(message), 4096)]
                for i, part in enumerate(parts):
                    await update.message.reply_text(part, parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(message, parse_mode=ParseMode.HTML)

        except Exception as e:
            logger.error(f"Ошибка при показе участников: {e}")
            await update.message.reply_text("Произошла ошибка при получении списка участников.")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback-запросов от inline-кнопок"""
        try:
            query = update.callback_query
            
            # Проверяем доступ
            if not await self.check_access(update):
                await query.answer("У вас нет доступа к этой функции")
                return
                
            # Обработка запроса на загрузку файла
            if query.data.startswith("upload_file:"):
                user_prompt = query.data.split(":", 1)[1]
                await query.answer("Пожалуйста, отправьте файл в ответ на сообщение")
                return
                
        except Exception as e:
            logger.error(f"❌ Ошибка в обработчике callback: {str(e)}")
            await query.answer("Произошла ошибка при обработке запроса")

    async def initialize(self, application: Application):
        """Инициализация приложения"""
        try:
            # Инициализация компонентов бота
            await self.setup(application)
            logger.info("✅ Компоненты бота инициализированы")

            # Регистрация обработчиков с фильтром группы
            allowed_group_filter = filters.Chat(chat_id=self.allowed_group_id)

            # Основные команды (доступны всем)
            application.add_handler(CommandHandler("help", self.help, filters=allowed_group_filter))
            application.add_handler(CommandHandler("info", self.info, filters=allowed_group_filter))
            application.add_handler(CommandHandler("register", self.register, filters=allowed_group_filter))
            application.add_handler(CommandHandler(
                "update_profile", self.update_profile, filters=allowed_group_filter))
            application.add_handler(CommandHandler("members", self.members, filters=allowed_group_filter))
            
            # Административные команды (с проверкой is_admin внутри обработчиков)
            application.add_handler(CommandHandler("clear_context", self.clear_context, filters=allowed_group_filter))
            application.add_handler(CommandHandler("botstats", self.show_stats, filters=allowed_group_filter))
            application.add_handler(CommandHandler(
                "update_system_prompt", self.update_system_prompt, filters=allowed_group_filter))
            application.add_handler(CommandHandler("backup", self.backup_database, filters=allowed_group_filter))
            
            # ВРЕМЕННО: команда для удаления всех пользователей (только для теста)
            application.add_handler(CommandHandler("clear_all_users", self.clear_all_users, filters=allowed_group_filter))
            
            # Обработчик текстовых сообщений с фильтром обращений к боту
            message_filters = (
                filters.TEXT 
                & ~filters.COMMAND 
                & allowed_group_filter
                & (
                    filters.Regex(pattern=r'(?i)^(брат|бро|@AiBratBot)\b')  # Прямое обращение к боту
                )
            )
            
            # Отдельный обработчик для ответов на сообщения бота
            reply_filters = (
                (filters.TEXT | filters.Document.ALL | filters.PHOTO)
                & ~filters.COMMAND 
                & allowed_group_filter
                & filters.REPLY
            )
            
            # Добавляем оба обработчика
            application.add_handler(
                MessageHandler(
                    message_filters,
                    self.handle_message
                )
            )
            
            application.add_handler(
                MessageHandler(
                    reply_filters,
                    self.handle_message
                )
            )

            # Обработчик для регистрации и обновления профиля (ставим в КОНЕЦ)
            application.add_handler(
                MessageHandler(
                    (filters.TEXT | filters.REPLY) & allowed_group_filter,
                    self.handle_registration_or_update
                )
            )

            # Команда welcome (только для allowed_group_filter)
            application.add_handler(CommandHandler("welcome", self.welcome, filters=allowed_group_filter))

            # Тестовая команда brat_privs (без фильтра)
            application.add_handler(CommandHandler("brat_privs", self.welcome))

            # Добавляем обработчик новых участников
            application.add_handler(ChatMemberHandler(self.greet_new_member, ChatMemberHandler.CHAT_MEMBER))

            logger.info(f"🚀 Бот настроен для работы в группе {self.allowed_group_id}")
            logger.info("✅ Все команды бота успешно зарегистрированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации приложения: {e}")
            raise

    async def get_topic_info(self, message: Message) -> dict:
        """Получение информации о текущем топике"""
        topic_info = {
            'topic_id': None,
            'topic_name': None,
            'is_topic': False
        }
        
        try:
            if message.is_topic_message:
                topic_info['is_topic'] = True
                topic_info['topic_id'] = message.message_thread_id
                # Получаем название топика, если возможно
                if message.reply_to_message and message.reply_to_message.forum_topic_created:
                    topic_info['topic_name'] = message.reply_to_message.forum_topic_created.name
                logger.info(f"📌 Сообщение в топике: {topic_info['topic_name']} (ID: {topic_info['topic_id']})")
            else:
                logger.info("📝 Сообщение в основном чате")
        except Exception as e:
            logger.error(f"❌ Ошибка при получении информации о топике: {e}")
            
        return topic_info

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка входящих сообщений"""
        try:
            user_id = update.effective_user.id
            message = update.message
            chat_id = update.effective_chat.id
            message_text = message.text or message.caption
            # --- Новая логика: регистрация/обновление профиля через 'брат профиль' ---
            if message_text:
                lowered = message_text.lower()
                if lowered.startswith('брат профиль'):
                    # Берём всё после 'брат профиль' как данные
                    profile_text = message_text[len('брат профиль'):].strip()
                    profile_data = await self.db.parse_registration_message(profile_text)
                    if not profile_data:
                        await message.reply_text(
                            "❌ Не удалось распознать данные. Пожалуйста, используйте предложенный формат."
                        )
                        return
                    # Проверяем, есть ли уже профиль
                    user_info = await self.db.get_user_info(user_id)
                    if user_info:
                        # Обновляем только указанные поля
                        for key in user_info:
                            if key not in profile_data:
                                profile_data[key] = user_info[key]
                    # Сохраняем профиль
                    try:
                        with self.db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                            exists = cursor.fetchone()
                            if exists:
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
                        await self.update_prompt_with_users()
                        await message.reply_text("✅ Профиль успешно сохранён!")
                    except Exception as e:
                        logger.error(f"Ошибка при сохранении профиля: {e}")
                        await message.reply_text("❌ Произошла ошибка при сохранении профиля. Попробуйте позже.")
                    return
            # --- Конец новой логики ---
            # ... existing code ...

            # Проверка ограничений
            is_allowed, error_message = self.rate_limiter.is_allowed(user_id, chat_id)
            if not is_allowed:
                await message.reply_text(error_message)
                await self.rate_limiter.log_suspicious_activity(
                    user_id, 
                    chat_id,
                    f"Превышение лимита запросов: {message.text[:100]}..."
                )
                return
                
            # Проверка на спам/флуд
            if message.text and len(message.text) > 4096:
                await message.reply_text("Сообщение слишком длинное. Максимальная длина: 4096 символов.")
                await self.rate_limiter.log_suspicious_activity(
                    user_id,
                    chat_id,
                    "Попытка отправки слишком длинного сообщения"
                )
                return
                
            logger.info("🔄 Получено новое сообщение")
            logger.info(f"👤 От пользователя: {user_id}")
            logger.info(f"💭 В чате: {chat_id}")
            
            # Получаем информацию о топике
            topic_info = await self.get_topic_info(message)
            
            # Получаем текст сообщения или подпись к файлу
            message_text = message.text or message.caption
            logger.info(f"📝 Текст сообщения: {message_text}")

            # Проверяем обращение к боту
            is_bot_mention = False
            if message_text:
                is_bot_mention = (
                    re.match(r'(?i)^(брат|бро|@AiBratBot)\b', message_text) or
                    (message.reply_to_message and message.reply_to_message.from_user and 
                     message.reply_to_message.from_user.username == context.bot.username)
                )
                logger.info(f"🤖 Обращение к боту: {'да' if is_bot_mention else 'нет'}")

            # Если нет обращения к боту, игнорируем
            if not is_bot_mention:
                logger.debug("Сообщение не содержит обращения к боту")
                return

            # Проверяем наличие файла
            file_info = None
            if message.document:
                logger.info(f"📄 Получен документ, но обработка файлов временно отключена")
            elif message.photo:
                logger.info("🖼 Получено фото, но обработка файлов временно отключена")
            elif message.video:
                logger.info("🎥 Получено видео, но обработка файлов временно отключена")
            elif message.audio:
                logger.info("🎵 Получен аудиофайл, но обработка файлов временно отключена")
            elif message.voice:
                logger.info("🎤 Получено голосовое сообщение, но обработка файлов временно отключена")

            # Обрабатываем текстовые команды
            try:
                # Проверяем запрос на генерацию изображения
                photo_match = re.search(PHOTO_PATTERN, message_text, re.IGNORECASE)
                if photo_match and self.image_generator:
                    prompt = photo_match.group(1).strip()
                    processing_msg = await message.reply_text("🎨 Генерирую изображение...")
                    try:
                        image_url = await self.image_generator.generate_image(prompt)
                        await message.reply_photo(image_url, caption=f"🖼 Сгенерировано по запросу: {prompt}")
                        await processing_msg.delete()
                        return
                    except Exception as e:
                        logger.error(f"Ошибка при генерации изображения: {e}")
                        await processing_msg.delete()
                        await message.reply_text("❌ Не удалось сгенерировать изображение. Попробуйте другой запрос.")
                        return

                # Проверяем запрос на поиск в интернете
                for pattern in WEB_SEARCH_PATTERNS:
                    web_match = re.search(pattern, message_text, re.IGNORECASE)
                    if web_match and self.perplexity:
                        query = web_match.group(1).strip()
                        processing_msg = await message.reply_text("🔍 Ищу информацию...")
                        try:
                            search_result = await self.perplexity.search(query)
                            await message.reply_text(f"🌐 Результаты поиска:\n\n{search_result}")
                            await processing_msg.delete()
                            return
                        except Exception as e:
                            logger.error(f"Ошибка при поиске: {e}")
                            await processing_msg.delete()
                            await message.reply_text("❌ Не удалось выполнить поиск. Попробуйте позже.")
                            return

                # Формируем контекст сообщения с учетом топика
                context_message = message_text
                if topic_info['is_topic'] and topic_info['topic_name']:
                    context_message = f"[В топике: {topic_info['topic_name']}] {message_text}"
            
            except Exception as e:
                logger.error(f"❌ Ошибка при обработке команды: {str(e)}")
                await message.reply_text("Произошла ошибка при обработке команды. Попробуйте позже.")

            # Получаем полный контекст из базы данных
            logger.info("📚 Получаю полный контекст диалога из базы данных")
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT role, content, timestamp 
                        FROM message_context 
                        WHERE user_id = ? 
                        ORDER BY timestamp ASC
                    """, (user_id,))
                    rows = cursor.fetchall()
                    full_context = [{"role": row[0], "content": row[1]} for row in rows]
                    logger.info(f"📊 Получено {len(full_context)} сообщений из контекста")
                    
                    # Добавляем текущее сообщение в контекст
                    cursor.execute("""
                        INSERT INTO message_context (user_id, role, content)
                        VALUES (?, 'user', ?)
                    """, (user_id, context_message))
                    conn.commit()
                    
                    # Обновляем полный контекст с новым сообщением
                    full_context.append({"role": "user", "content": context_message})
                    
                    # Получаем ответ от модели с полным контекстом
                    response = await self.get_model_response(full_context, user_id)
                    
                    if response:
                        # Добавляем ответ бота в контекст
                        cursor.execute("""
                            INSERT INTO message_context (user_id, role, content)
                            VALUES (?, 'assistant', ?)
                        """, (user_id, response))
                        conn.commit()
                        
                        await message.reply_text(response)
                        logger.info(f"✅ Ответ успешно отправлен пользователю {user_id}")
                    else:
                        await message.reply_text(
                            "Извините, не удалось сгенерировать ответ. Попробуйте переформулировать вопрос."
                        )
                        logger.warning(f"⚠️ Не удалось сгенерировать ответ для пользователя {user_id}")
                        
            except Exception as e:
                logger.error(f"❌ Ошибка при работе с базой данных: {str(e)}")
                await message.reply_text(
                    "Произошла ошибка при обработке вашего сообщения. Попробуйте позже."
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации ответа: {str(e)}")
            await message.reply_text(
                "Произошла ошибка при обработке вашего сообщения. Попробуйте позже."
            )

    async def setup_commands(self, application: Application):
        """Настройка команд бота"""
        try:
            # Основные команды (доступны всем)
            base_commands = [
                BotCommand("help", "Показать справку"),
                BotCommand("info", "Информация о сообществе"),
                BotCommand("register", "Зарегистрироваться в сообществе"),
                BotCommand("update_profile", "Обновить информацию о себе"),
                BotCommand("members", "Показать участников сообщества")
            ]

            # Административные команды
            admin_commands = [
                BotCommand("clear_context", "Очистить контекст диалога"),
                BotCommand("stats", "Показать статистику использования"),
                BotCommand("update_system_prompt", "Обновить системный промпт"),
                BotCommand("backup", "Создать резервную копию данных")
            ]

            # Устанавливаем базовые команды для всех пользователей
            await application.bot.delete_my_commands()  # Сначала удаляем все команды
            await application.bot.set_my_commands(base_commands)  # Устанавливаем базовые команды

            # Создаем отдельный список команд для администраторов
            chat_admins = await application.bot.get_chat_administrators(self.allowed_group_id)
            admin_ids = [admin.user.id for admin in chat_admins]

            logger.info(f"Настроены базовые команды для всех пользователей")
            logger.info(f"Найдено {len(admin_ids)} администраторов")

        except Exception as e:
            logger.error(f"Ошибка при настройке команд: {e}")
            raise

    async def clear_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка контекста диалога. Админ может указать user_id или @username."""
        if not await self.check_access(update):
            return
        user_id = update.effective_user.id
        is_admin = await self.is_admin(update)
        target_user_id = user_id
        # Если есть аргумент и вызывающий — админ
        if context.args and is_admin:
            arg = context.args[0]
            if arg.startswith('@'):
                # Поиск по username
                username = arg.lstrip('@')
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM users WHERE telegram_nick = ?", (username,))
                    row = cursor.fetchone()
                    if row:
                        target_user_id = row[0]
                    else:
                        await update.message.reply_text(f"Пользователь с ником @{username} не найден.")
                        return
            else:
                # Поиск по user_id
                try:
                    target_user_id = int(arg)
                except ValueError:
                    await update.message.reply_text("Некорректный user_id. Используйте /clear_context user_id или /clear_context @username")
                    return
        elif context.args and not is_admin:
            await update.message.reply_text("Эта функция доступна только администраторам.")
            return
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM message_context WHERE user_id = ?", (target_user_id,))
                cursor.execute("DELETE FROM chat_summaries WHERE user_id = ?", (target_user_id,))
                conn.commit()
            if target_user_id == user_id:
                await update.message.reply_text("✅ Ваш контекст диалога очищен")
            else:
                await update.message.reply_text(f"✅ Контекст пользователя {target_user_id} очищен (или по нику)")
        except Exception as e:
            logger.error(f"Ошибка при очистке контекста: {e}")
            await update.message.reply_text("❌ Произошла ошибка при очистке контекста")

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику использования бота"""
        if not await self.check_access(update):
            return
            
        if not await self.is_admin(update):
            # Тихо игнорируем команду от не-администраторов
            return

        try:
            logger.info("🔄 Начинаю сбор статистики...")
            
            # Базовая статистика из rate_limiter
            total_messages = len(self.rate_limiter.user_limits)
            blocked_users = len(self.rate_limiter.blocked_users)
            current_load = len(self.rate_limiter.group_limits)
            
            logger.info(f"📊 Rate Limiter статистика: messages={total_messages}, blocked={blocked_users}, load={current_load}")

            # Получаем статистику по контекстам из базы данных
            context_stats = {}
            summary_count = 0
            
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Получаем количество сообщений для каждого пользователя
                    cursor.execute("""
                        SELECT user_id, COUNT(*) as msg_count 
                        FROM message_context 
                        GROUP BY user_id
                    """)
                    rows = cursor.fetchall()
                    logger.info(f"📊 Найдено {len(rows)} пользователей с сообщениями")
                    
                    for user_id, msg_count in rows:
                        context_stats[user_id] = msg_count
                        # Получаем последние сообщения пользователя
                        cursor.execute("""
                            SELECT role, content, timestamp 
                            FROM message_context 
                            WHERE user_id = ? 
                            ORDER BY timestamp DESC 
                            LIMIT 5
                        """, (user_id,))
                        last_messages = cursor.fetchall()
                        logger.info(f"👤 Пользователь {user_id}:")
                        logger.info(f"   • Всего сообщений: {msg_count}")
                        logger.info(f"   • Последние сообщения:")
                        for role, content, timestamp in last_messages:
                            logger.info(f"     - [{timestamp}] {role}: {content[:50]}...")

                    # Получаем информацию о саммари
                    cursor.execute("SELECT COUNT(*) FROM chat_summaries")
                    summary_count = cursor.fetchone()[0]
                    logger.info(f"📝 Количество саммари в базе: {summary_count}")
                    
                    # Получаем детали последних саммари
                    cursor.execute("""
                        SELECT user_id, summary, created_at 
                        FROM chat_summaries 
                        ORDER BY created_at DESC 
                        LIMIT 5
                    """)
                    last_summaries = cursor.fetchall()
                    logger.info("📝 Последние саммари:")
                    for user_id, summary, created_at in last_summaries:
                        logger.info(f"   • Пользователь {user_id} [{created_at}]:")
                        logger.info(f"     {summary[:100]}...")
                    
                    # Проверяем пользователей с длинными контекстами
                    long_contexts = [user_id for user_id, count in context_stats.items() if count > 20]
                    logger.info(f"📊 Пользователи с длинными контекстами (>20): {long_contexts}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при получении данных из БД: {str(e)}")
                context_stats = {}
                summary_count = 0

            # Анализируем контексты
            total_context_messages = sum(context_stats.values())
            users_with_long_context = sum(1 for count in context_stats.values() if count > 20)
            max_context_length = max(context_stats.values()) if context_stats else 0
            avg_context_length = total_context_messages / len(context_stats) if context_stats else 0
            
            logger.info(f"📊 Итоговая статистика:")
            logger.info(f"   • Всего сообщений: {total_context_messages}")
            logger.info(f"   • Пользователей: {len(context_stats)}")
            logger.info(f"   • Средняя длина контекста: {avg_context_length:.1f}")
            logger.info(f"   • Максимальная длина: {max_context_length}")
            logger.info(f"   • Саммари: {summary_count}")

            # Формируем подробный отчет
            stats_text = (
                "🤖 Статистика бота Брат\n\n"
                "💭 Статистика контекстов:\n"
                f"• Пользователей с контекстом: {len(context_stats)}\n"
                f"• Всего сообщений в контекстах: {total_context_messages}\n"
                f"• Средняя длина контекста: {avg_context_length:.1f} сообщений\n"
                f"• Максимальная длина контекста: {max_context_length} сообщений\n"
                f"• Пользователей с длинным контекстом (>20): {users_with_long_context}\n\n"
                
                "🔄 Саммаризация:\n"
                f"• Количество сохраненных саммари: {summary_count}\n"
                "• Активируется при: >20 сообщений\n"
                "• Сохраняет: последние 10 сообщений\n"
                "• Создает: краткое содержание предыдущего диалога\n\n"
                
                "⚡️ Текущее состояние:\n"
                f"• Активных пользователей: {total_messages}\n"
                f"• Заблокированных пользователей: {blocked_users}\n"
                f"• Текущая нагрузка: {current_load} групп\n"
            )
            
            logger.info("✅ Статистика собрана успешно")
            
            # Отправляем статистику лично администратору
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=stats_text,
                parse_mode=None  # Отключаем parse mode для избежания ошибок форматирования
            )
            
            # Удаляем команду из группы
            try:
                await update.message.delete()
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики: {str(e)}")
            # Отправляем сообщение об ошибке лично администратору
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"❌ Произошла ошибка при получении статистики: {str(e)}"
            )

    async def update_system_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновление системного промпта"""
        if not await self.check_access(update):
            return
            
        if not await self.is_admin(update):
            await update.message.reply_text("⚠️ Эта команда доступна только администраторам группы")
            return

        try:
            # Получаем новый промпт из сообщения
            if not context.args:
                await update.message.reply_text(
                    "Пожалуйста, укажите новый системный промпт после команды"
                )
                return
                
            new_prompt = " ".join(context.args)
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES ('system_prompt', ?, datetime('now'))
                """, (new_prompt,))
                conn.commit()
            self.system_prompt = new_prompt
            
            await update.message.reply_text("✅ Системный промпт успешно обновлен")
        except Exception as e:
            logger.error(f"Ошибка при обновлении промпта: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обновлении промпта")

    async def backup_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание резервной копии базы данных"""
        if not await self.check_access(update):
            return
            
        if not await self.is_admin(update):
            await update.message.reply_text("⚠️ Эта команда доступна только администраторам группы")
            return

        try:
            backup_dir = pathlib.Path('backup')
            backup_dir.mkdir(exist_ok=True)
            
            # Создаем имя файла с текущей датой
            backup_file = backup_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Получаем данные для бэкапа
            backup_data = {}
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем все сообщения
                cursor.execute("SELECT user_id, role, content, timestamp FROM message_context")
                backup_data['messages'] = [
                    {
                        'user_id': row[0],
                        'role': row[1],
                        'content': row[2],
                        'timestamp': row[3]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Получаем все саммари
                cursor.execute("SELECT user_id, summary, created_at FROM chat_summaries")
                backup_data['summaries'] = [
                    {
                        'user_id': row[0],
                        'summary': row[1],
                        'created_at': row[2]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Получаем все настройки
                cursor.execute("SELECT key, value, updated_at FROM settings")
                backup_data['settings'] = [
                    {
                        'key': row[0],
                        'value': row[1],
                        'updated_at': row[2]
                    }
                    for row in cursor.fetchall()
                ]
            
            # Сохраняем бэкап
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
            await update.message.reply_text(
                f"✅ Резервная копия создана: {backup_file.name}"
            )
        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа: {e}")
            await update.message.reply_text("❌ Произошла ошибка при создании резервной копии")

    def run(self):
        """Запуск бота"""
        try:
            # Создаем приложение
            application = Application.builder().token(TOKEN).build()

            # Настраиваем и запускаем бота
            application.post_init = self.initialize
            application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")
            raise

    async def shutdown(self, application: Application) -> None:
        """Корректное завершение работы бота"""
        logger.info("🔄 Завершение работы бота...")

    async def convert_document(self, file_data: bytes, file_name: str) -> str:
        """Конвертирует документ в Markdown используя MarkItDown"""
        try:
            # Создаем объект BytesIO из данных файла
            file_stream = io.BytesIO(file_data)
            file_stream.name = file_name  # Устанавливаем имя файла для определения типа

            # Конвертируем документ
            result = self.markitdown.convert_stream(file_stream)
            return result.text_content

        except Exception as e:
            logger.error(f"❌ Ошибка при конвертации документа: {str(e)}")
            raise

    async def is_admin(self, update: Update) -> bool:
        """Проверка является ли пользователь администратором группы"""
        if not update.effective_chat or not update.effective_user:
            return False
            
        try:
            chat_member = await update.effective_chat.get_member(update.effective_user.id)
            return chat_member.status in ['creator', 'administrator']
        except Exception as e:
            logger.error(f"Ошибка при проверке прав администратора: {e}")
            return False

    def setup_database(self):
        """Настройка базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Создаем таблицу для контекста сообщений
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Создаем таблицу для саммари
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
            
            conn.commit()

    def update_system_prompt(self, new_prompt: str):
        """Обновить системный промпт"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES ('system_prompt', ?, datetime('now'))
            """, (new_prompt,))
            conn.commit()

    async def clear_all_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаляет всех пользователей из базы (только для теста/админа)"""
        if not await self.is_admin(update):
            await update.message.reply_text("Только для администратора!")
            return
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users")
                conn.commit()
            await update.message.reply_text("✅ Все пользователи удалены из базы!")
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователей: {e}")
            await update.message.reply_text("❌ Ошибка при удалении пользователей")

    async def welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет приветственное сообщение пользователю"""
        if not await self.check_access(update):
            return
        user = update.effective_user
        name = user.first_name or user.full_name or 'друг'
        welcome_text = (
            f"Привет! 🤖✌️ {name}\n\n"
            "Рад тебя видеть в комьюнити AiTouch!\n"
            "Я — бот-брат, карманный помощник, обитающий в этом чате.\n\n"
            "Не просто чат-бот, а тот, кто:\n"
            "— Подскажет, куда идти и с кем лучше пообщаться\n"
            "— Свяжет тебя с нужными людьми для сотрудничества\n"
            "— Поможет сгенерить текст, идею или картинку (я тоже немного ИИ, если что 👀)\n\n"
            "📌 Перед тем как вливаться в движ, заполни, пожалуйста, короткую анкету:\n"
            "👉 /register\n\n"
            "Это нужно, чтобы я понимал, кто ты, и в какой момент тебе порекомендовать полезный контакт (или порекомендовать тебя как полезный контакт).\n"
            "Моя миссия — делать удобно и полезно.\n\n"
            "⚠️ В сообществе есть простые правила общения, без токсичности, спама и прочего негатива.\n"
            "🧾 [Правила AiTouch Community](https://telegra.ph/Pravila-AiTouch-Community-04-23)\n\n"
            "🎉 Не бойся писать в чатах — тут все свои. Можно задавать вопросы, делиться опытом, искать ответы, мемы, инсайты и инсайды.\n\n"
            "Главное - прочитай закреплённые сообщения в каждом чате, чтобы разобраться в темах.\n\n"
            "На связи твой бот-брат 🤖\n"
            "Если что — просто пиши 'брат', всегда рядом 🤙"
        )
        logger.info(f"[WELCOME] Пробую отправить приветственное сообщение для {name} (user_id={user.id})")
        try:
            msg = await update.message.reply_text(welcome_text, disable_web_page_preview=True, parse_mode='Markdown')
            context.user_data['welcome_msg_id'] = msg.message_id
            logger.info(f"[WELCOME] Приветственное сообщение отправлено (msg_id={msg.message_id})")
        except Exception as e:
            logger.error(f"[WELCOME] Ошибка при отправке приветственного сообщения: {e}")

    async def greet_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Автоматическое приветствие новых участников группы"""
        chat_member = update.chat_member
        if chat_member.new_chat_member.status == "member":
            user = chat_member.new_chat_member.user
            name = user.first_name or user.full_name or 'друг'
            welcome_text = (
                f"Привет! 🤖✌️ {name}\n\n"
                "Рад тебя видеть в комьюнити AiTouch!\n"
                "Я — бот-брат, карманный помощник, обитающий в этом чате.\n\n"
                "Не просто чат-бот, а тот, кто:\n"
                "— Подскажет, куда идти и с кем лучше пообщаться\n"
                "— Свяжет тебя с нужными людьми для сотрудничества\n"
                "— Поможет сгенерить текст, идею или картинку (я тоже немного ИИ, если что 👀)\n\n"
                "📌 Перед тем как вливаться в движ, заполни, пожалуйста, короткую анкету:\n"
                "👉 /register\n\n"
                "Это нужно, чтобы я понимал, кто ты, и в какой момент тебе порекомендовать полезный контакт (или порекомендовать тебя как полезный контакт).\n"
                "Моя миссия — делать удобно и полезно.\n\n"
                "⚠️ В сообществе есть простые правила общения, без токсичности, спама и прочего негатива.\n"
                "🧾 [Правила AiTouch Community](https://telegra.ph/Pravila-AiTouch-Community-04-23)\n\n"
                "🎉 Не бойся писать в чатах — тут все свои. Можно задавать вопросы, делиться опытом, искать ответы, мемы, инсайты и инсайды.\n\n"
                "Главное - прочитай закреплённые сообщения в каждом чате, чтобы разобраться в темах.\n\n"
                "На связи твой бот-брат 🤖\n"
                "Если что — просто пиши 'брат', всегда рядом 🤙"
            )
            msg = await context.bot.send_message(
                chat_id=chat_member.chat.id,
                text=welcome_text,
                disable_web_page_preview=True,
                parse_mode='Markdown'
            )
            # Сохраняем message_id приветствия в chat_data
            context.chat_data['welcome_msg_id'] = msg.message_id
            # Запускаем задачу на удаление через минуту
            import asyncio
            asyncio.create_task(self._delete_welcome_later(context, chat_member.chat.id, msg.message_id))

    async def _delete_welcome_later(self, context, chat_id, message_id):
        await asyncio.sleep(180)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass

if __name__ == '__main__':
    # Создаем и запускаем бота
    bot = BratBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise 