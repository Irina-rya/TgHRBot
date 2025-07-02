# TgHRBot

Корпоративный Telegram-бот для HR с интеграцией GigaChat

## Возможности
- Проведение интервью по направлениям QA и Менеджер по продажам
- Автоматическая оценка и уточнение ответов кандидата через GigaChat
- Формирование итогового резюме и отправка HR-специалисту

## Архитектура
- `bot/` — логика Telegram-бота, FSM, сценарии
- `giga/` — работа с GigaChat API (токен, запросы)
- `questions/` — вопросы по направлениям
- `utils/` — логирование и вспомогательные функции
- `config.py` — настройки, токены
- `main.py` — точка входа

## Запуск
1. Установите зависимости:
   ```
   pip install -r requirements.txt
   ```
2. Укажите токены и настройки в `.env` или `config.py`
3. Запустите бота:
   ```
   python main.py
   ```

## Настройки
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота
- `GIGACHAT_AUTH` — ключ авторизации GigaChat
- `HR_TELEGRAM_ID` — Telegram ID HR для отправки резюме

## Пример .env
```
TELEGRAM_BOT_TOKEN=your_telegram_token
GIGACHAT_AUTH=your_gigachat_auth
HR_TELEGRAM_ID=your_hr_id
``` 