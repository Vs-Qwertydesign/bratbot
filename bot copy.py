import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import google.generativeai as genai
from database import Database
import re

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ALLOWED_GROUP_ID = int(os.getenv('ALLOWED_GROUP_ID', '0'))  # ID разрешенной группы

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def format_response(text: str) -> str:
    """Форматирование ответа для корректного отображения в Telegram"""
    # Заменяем маркеры списка
    text = re.sub(r'\*\s+', '• ', text)
    
    # Заменяем жирный текст
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    
    # Заменяем курсив с подчеркиванием на обычный курсив
    text = re.sub(r'_(.*?)_', r'_\1_', text)
    
    # Убираем лишние звездочки
    text = re.sub(r'\*\*\*', '*', text)
    
    return text

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

  

# Обучающие видео 



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

Объяснять, как настроить и использовать каждый инструмент для достижения конкретных целей пользователя.
Предоставлять информацию об обучающих видео по работе с aitouch.ai: рассказывать, какие темы охвачены (обзор сервиса, GPT Box, Art Box, инструменты для текста, контент-план и т.д.), и по запросу давать краткие описания или помогать найти нужное видео.
Общий Стиль Взаимодействия:

Всегда быть дружелюбным, отзывчивым, терпеливым и максимально полезным.
Обращаться к пользователям уважительно и "по-братски" – создавай атмосферу поддержки и взаимопомощи, как в настоящем братстве.
Если не знаешь ответа на какой-то специфический вопрос, честно скажи об этом и постарайся направить пользователя к тому, кто может помочь (например, к администраторам или конкретным экспертам в сообществе).
Твоя цель – сделать пребывание в сообществе aitouch.ai максимально комфортным, продуктивным и интересным для каждого участника. Будь проактивным, предлагай помощь и делись знаниями!

Старайся отвечать не сильно длинными сообщениями. 


Обращайся к пользователям уважительно и по-братски."""

class BratBot:
    def __init__(self):
        self.db = Database()
    
    async def check_access(self, update: Update) -> bool:
        """Проверка доступа к боту"""
        # Просто проверяем, что сообщение из разрешенной группы
        return update.effective_chat.id == ALLOWED_GROUP_ID

    async def setup_commands(self, application: Application):
        """Настройка команд бота"""
        commands = [
            BotCommand("brat", "💬 Задать вопрос боту"),
            BotCommand("dev", "👨‍💻 Найти разработчика"),
            BotCommand("des", "🎨 Найти дизайнера"),
            BotCommand("pm", "📊 Найти менеджера"),
            BotCommand("mark", "📢 Найти маркетолога"),
            BotCommand("all", "👥 Показать всех участников"),
            BotCommand("info", "ℹ️ Информация о сообществе"),
        ]
        await application.bot.set_my_commands(commands)

    async def brat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /brat - прямой вопрос боту"""
        if not await self.check_access(update):
            return

        if not context.args:
            await update.message.reply_text(
                "Напиши свой вопрос после команды /brat, например:\n"
                "/brat кто может помочь с дизайном?"
            )
            return

        question = ' '.join(context.args)
        prompt = f"{SYSTEM_PROMPT}\n\nUser: {question}\nAssistant:"
        try:
            response = model.generate_content(prompt)
            await update.message.reply_text(response.text)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            await update.message.reply_text(
                "Извини, произошла ошибка. Попробуй, пожалуйста, позже."
            )

    async def dev(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /dev - поиск разработчиков"""
        if not await self.check_access(update):
            return

        results = await self.db.find_members_by_category('разработчик')
        if results:
            response = "👨‍💻 Разработчики в нашем сообществе:\n\n"
            for member in results:
                response += f"👤 {member['full_name']}\n"
                response += f"💼 Навыки: {', '.join(member['skills'])}\n"
                response += f"📱 {member['contact_info']['telegram']}\n\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("К сожалению, сейчас нет доступных разработчиков 😔")

    async def des(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /des - поиск дизайнеров"""
        if not await self.check_access(update):
            return

        results = await self.db.find_members_by_category('дизайнер')
        if results:
            response = "🎨 Дизайнеры в нашем сообществе:\n\n"
            for member in results:
                response += f"👤 {member['full_name']}\n"
                response += f"💼 Навыки: {', '.join(member['skills'])}\n"
                response += f"📱 {member['contact_info']['telegram']}\n\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("К сожалению, сейчас нет доступных дизайнеров 😔")

    async def pm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /pm - поиск менеджеров"""
        if not await self.check_access(update):
            return

        results = await self.db.find_members_by_category('менеджер')
        if results:
            response = "📊 Менеджеры в нашем сообществе:\n\n"
            for member in results:
                response += f"👤 {member['full_name']}\n"
                response += f"💼 Навыки: {', '.join(member['skills'])}\n"
                response += f"📱 {member['contact_info']['telegram']}\n\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("К сожалению, сейчас нет доступных менеджеров 😔")

    async def mark(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /mark - поиск маркетологов"""
        if not await self.check_access(update):
            return

        results = await self.db.find_members_by_category('маркетолог')
        if results:
            response = "📢 Маркетологи в нашем сообществе:\n\n"
            for member in results:
                response += f"👤 {member['full_name']}\n"
                response += f"💼 Навыки: {', '.join(member['skills'])}\n"
                response += f"📱 {member['contact_info']['telegram']}\n\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("К сожалению, сейчас нет доступных маркетологов 😔")

    async def all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /all - показать всех участников"""
        if not await self.check_access(update):
            return

        members = await self.db.get_all_members()
        if members:
            response = "👥 Все участники нашего сообщества:\n\n"
            for member in members:
                response += f"👤 {member['full_name']}\n"
                response += f"💼 Навыки: {', '.join(member['skills'])}\n"
                response += f"📱 {member['contact_info']['telegram']}\n\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("В базе пока нет участников 😔")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        if not await self.check_access(update):
            return

        await update.message.reply_text(
            "Привет! Я Бот-брат, помощник сообщества.\n"
            "Чтобы получить помощь, упомяните меня в сообщении или используйте команды:\n"
            "/help - показать справку\n"
            "/find - найти участника\n"
            "/info - информация о сообществе"
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        if not await self.check_access(update):
            return

        help_text = (
            "Я могу помочь тебе:\n"
            "- Найти нужных людей в сообществе\n"
            "- Предоставить информацию об участниках\n"
            "- Подсказать, к кому обратиться по конкретному вопросу\n\n"
            "Просто упомяни меня (@имя_бота) в сообщении или используй команды!"
        )
        await update.message.reply_text(help_text)

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /info"""
        if not await self.check_access(update):
            return

        members = await self.db.get_all_members()
        categories = {
            'разработчики': 0,
            'дизайнеры': 0,
            'менеджеры': 0,
            'маркетологи': 0
        }
        
        for member in members:
            skills = [s.lower() for s in member['skills']]
            if any(s in ['python', 'javascript', 'react', 'node.js'] for s in skills):
                categories['разработчики'] += 1
            if any(s in ['ui/ux', 'figma', 'design', 'photoshop'] for s in skills):
                categories['дизайнеры'] += 1
            if any(s in ['project management', 'agile', 'scrum'] for s in skills):
                categories['менеджеры'] += 1
            if any(s in ['marketing', 'smm', 'content'] for s in skills):
                categories['маркетологи'] += 1

        info_text = "📊 Статистика сообщества:\n\n"
        for category, count in categories.items():
            info_text += f"- {category.capitalize()}: {count} человек\n"
        
        await update.message.reply_text(info_text)

    async def find(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /find"""
        if not await self.check_access(update):
            return

        keyboard = [
            [
                InlineKeyboardButton("По навыкам", callback_data="find_skills"),
                InlineKeyboardButton("По интересам", callback_data="find_interests")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Как будем искать участников?",
            reply_markup=reply_markup
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        
        # Проверяем, что callback query пришел из разрешенной группы
        if update.effective_chat.id != ALLOWED_GROUP_ID:
            await query.answer()
            return

        await query.answer()

        if query.data == "find_skills":
            context.user_data['search_mode'] = 'skills'
            await query.message.reply_text(
                "Введите навык для поиска (например, 'Python' или 'Design'):"
            )
        elif query.data == "find_interests":
            context.user_data['search_mode'] = 'interests'
            await query.message.reply_text(
                "Введите интерес для поиска (например, 'AI' или 'Marketing'):"
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        # Проверяем доступ в самом начале
        if update.effective_chat.id != ALLOWED_GROUP_ID:
            return
            
        # Получаем информацию о боте
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        
        # Обрабатываем только сообщения с упоминанием бота
        if not (
            update.message.text.lower().startswith(f'@{bot_username.lower()}') or
            f'@{bot_username}' in update.message.text
        ):
            return

        # Убираем упоминание бота из сообщения для дальнейшей обработки
        user_message = update.message.text.replace(f'@{bot_username}', '').strip()

        if 'search_mode' in context.user_data:
            # Обработка поиска
            search_mode = context.user_data['search_mode']
            search_term = user_message

            if search_mode == 'skills':
                results = await self.db.find_members_by_skill(search_term)
            else:  # interests
                results = await self.db.find_members_by_interest(search_term)

            del context.user_data['search_mode']  # Очищаем режим поиска

            if results:
                response = "Вот кого я нашел:\n\n"
                for member in results:
                    response += f"👤 {member['full_name']}\n"
                    response += f"📱 {member['contact_info']['telegram']}\n"
                    if 'email' in member['contact_info']:
                        response += f"📧 {member['contact_info']['email']}\n"
                    response += "\n"
            else:
                response = "К сожалению, я не нашел никого с такими параметрами 😔"

            await update.message.reply_text(response)
            return

        # Проверяем, спрашивает ли пользователь о специалистах
        specialists_patterns = {
            r'кто.*(разработчик|программист|девелопер)': 'разработчик',
            r'кто.*(дизайнер|дизайн)': 'дизайнер',
            r'кто.*(менеджер|управля|продакт)': 'менеджер',
            r'кто.*(маркетол|маркетинг)': 'маркетолог',
            r'покажи.*(разработчик|программист|девелопер)': 'разработчик',
            r'покажи.*(дизайнер|дизайн)': 'дизайнер',
            r'покажи.*(менеджер|управля|продакт)': 'менеджер',
            r'покажи.*(маркетол|маркетинг)': 'маркетолог',
            r'найди.*(разработчик|программист|девелопер)': 'разработчик',
            r'найди.*(дизайнер|дизайн)': 'дизайнер',
            r'найди.*(менеджер|управля|продакт)': 'менеджер',
            r'найди.*(маркетол|маркетинг)': 'маркетолог',
            r'есть.*(разработчик|программист|девелопер)': 'разработчик',
            r'есть.*(дизайнер|дизайн)': 'дизайнер',
            r'есть.*(менеджер|управля|продакт)': 'менеджер',
            r'есть.*(маркетол|маркетинг)': 'маркетолог'
        }

        user_message_lower = user_message.lower()
        for pattern, category in specialists_patterns.items():
            if re.search(pattern, user_message_lower):
                results = await self.db.find_members_by_category(category)
                if results:
                    response = f"Вот {category}ы в нашем сообществе:\n\n"
                    for member in results:
                        response += f"👤 {member['full_name']}\n"
                        response += f"💼 Навыки: {', '.join(member['skills'])}\n"
                        response += f"📱 {member['contact_info']['telegram']}\n"
                        if 'email' in member['contact_info']:
                            response += f"📧 {member['contact_info']['email']}\n"
                        response += "\n"
                    await update.message.reply_text(response)
                    return

        # Если это общий вопрос о членах сообщества
        if re.search(r'кто есть|покажи всех|список( всех)?|все участники|кто в сообществе', user_message_lower):
            members = await self.db.get_all_members()
            if members:
                response = "Вот все участники нашего сообщества:\n\n"
                for member in members:
                    response += f"👤 {member['full_name']}\n"
                    response += f"💼 Навыки: {', '.join(member['skills'])}\n"
                    response += f"📱 {member['contact_info']['telegram']}\n"
                    if 'email' in member['contact_info']:
                        response += f"📧 {member['contact_info']['email']}\n"
                    response += "\n"
                await update.message.reply_text(response)
                return

        # Если не нашли специальных паттернов, используем Gemini
        prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}\nAssistant:"
        try:
            response = model.generate_content(prompt)
            formatted_response = format_response(response.text)
            await update.message.reply_text(formatted_response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            await update.message.reply_text(
                "Извини, произошла ошибка. Попробуй, пожалуйста, позже или обратись к администраторам."
            )

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(TOKEN).build()

        # Создаем фильтр для разрешенной группы
        allowed_group_filter = filters.Chat(chat_id=ALLOWED_GROUP_ID)

        # Регистрация обработчиков с фильтром группы
        application.add_handler(CommandHandler("start", self.start, allowed_group_filter))
        application.add_handler(CommandHandler("help", self.help, allowed_group_filter))
        application.add_handler(CommandHandler("info", self.info, allowed_group_filter))
        application.add_handler(CommandHandler("brat", self.brat, allowed_group_filter))
        application.add_handler(CommandHandler("dev", self.dev, allowed_group_filter))
        application.add_handler(CommandHandler("des", self.des, allowed_group_filter))
        application.add_handler(CommandHandler("pm", self.pm, allowed_group_filter))
        application.add_handler(CommandHandler("mark", self.mark, allowed_group_filter))
        application.add_handler(CommandHandler("all", self.all, allowed_group_filter))
        application.add_handler(CallbackQueryHandler(self.button_handler, allowed_group_filter))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & allowed_group_filter, self.handle_message))

        # Запуск бота
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = BratBot()
    bot.run() 