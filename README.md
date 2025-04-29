# 🤖 Бот-брат (AiBratBot)

## 📋 Описание
Бот-помощник для сообщества aitouch.ai, построенный на базе Google Gemini API. Поддерживает генерацию изображений через Replicate API (SANA model), обработку файлов и поиск информации через Perplexity API.

## 🛠 Технические требования
- Python 3.10+
- Доступ к API:
  - Google Gemini API
  - Replicate API (SANA model)
  - Perplexity API
  - Telegram Bot API

## ⚙️ Установка и настройка

### 1. Клонирование репозитория
```bash
git clone [ваш-репозиторий]
cd [папка-проекта]
```

### 2. Создание виртуального окружения
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/Mac
# или
.venv\Scripts\activate  # для Windows
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения
Создайте файл `.env` в корневой директории:
```env
# Telegram Bot Token (получить у @BotFather)
TELEGRAM_TOKEN=ваш_токен_бота

# Google Gemini API Key
GEMINI_API_KEY=ваш_ключ_gemini

# Perplexity API Key
PERPLEXITY_API_KEY=ваш_ключ_perplexity

# Allowed Group ID
ALLOWED_GROUP_ID=ид_вашей_группы

# Replicate API Token
REPLICATE_API_TOKEN=ваш_токен_replicate

# Google API Key
GOOGLE_API_KEY=ваш_ключ_google
```

## 🚀 Запуск бота

### Локальный запуск
```bash
python bot.py
```

### Запуск на сервере через systemd
1. Создайте файл сервиса:
```bash
sudo nano /etc/systemd/system/bratbot.service
```

2. Добавьте конфигурацию:
```ini
[Unit]
Description=Brat Bot Service
After=network.target

[Service]
Type=simple
User=ваш_пользователь
WorkingDirectory=/путь/к/проекту
Environment=PATH=/путь/к/проекту/.venv/bin
ExecStart=/путь/к/проекту/.venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Активируйте сервис:
```bash
sudo systemctl enable bratbot
sudo systemctl start bratbot
```

## 📝 Возможности бота

### Основные команды (доступны всем)
- `/help` - показать справку
- `/info` - информация о сообществе
- `/register` - зарегистрироваться в сообществе
- `/update_profile` - обновить информацию о себе
- `/members` - показать участников сообщества

### Обработка файлов
- Отправьте файл с сообщением "брат изучи файл" для анализа содержимого
- Поддерживаются различные форматы файлов (документы, изображения, видео, аудио)
- Максимальный размер файла: 20 MB

### Генерация изображений
- `брат фото [описание]` - сгенерировать изображение используя SANA model
- Поддерживаются расширенные настройки генерации:
  - Формат вывода: JPG
  - Качество: 80
  - Guidance scale: 5.5
  - Inference steps: 2
  - Intermediate timesteps: 1.3

### Поиск информации
- `брат найди в сети [запрос]`
- `брат найди в интернете [запрос]`
- `брат поищи в сети [запрос]`
- `брат загугли [запрос]`

### Административные команды (только для администраторов группы)
- `/clear_context` - очистить контекст диалога
- `/stats` - показать статистику использования
- `/update_system_prompt` - обновить системный промпт
- `/backup` - создать резервную копию данных

## 🛡 Защита от DDoS

Бот имеет встроенную защиту от DDoS-атак:
- Ограничение количества запросов в минуту
- Блокировка спам-аккаунтов
- Защита от флуда сообщениями
- Мониторинг подозрительной активности

## 📊 Мониторинг

### Просмотр логов
```bash
# Просмотр логов сервиса
sudo journalctl -u bratbot -f

# Просмотр логов приложения
tail -f logs/bot.log
```

### Проверка статуса
```bash
sudo systemctl status bratbot
```

## 🔄 Обновление бота
```bash
# Остановка сервиса
sudo systemctl stop bratbot

# Обновление кода
git pull

# Обновление зависимостей
source .venv/bin/activate
pip install -r requirements.txt

# Запуск сервиса
sudo systemctl start bratbot
```

## ⚠️ Устранение неполадок

### Частые проблемы и решения
1. Бот не отвечает:
   - Проверьте правильность токенов в файле .env
   - Проверьте подключение к интернету
   - Проверьте доступность API сервисов

2. Ошибки генерации изображений:
   - Проверьте токен Replicate API
   - Убедитесь, что промпт не содержит запрещенного контента
   - Проверьте формат запроса

3. Ошибки при обработке файлов:
   - Проверьте размер файла (не более 20 MB)
   - Убедитесь, что формат файла поддерживается
   - Проверьте токен Google Gemini API
