from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from bot.states import InterviewStates
from questions.qa import QA_QUESTIONS
from questions.sales import SALES_QUESTIONS
from giga.api import gigachat_api
from config import HR_TELEGRAM_ID
from typing import Dict, List

router = Router()

DIRECTIONS: Dict[str, List[str]] = {
    'QA': QA_QUESTIONS,
    'Менеджер по продажам': SALES_QUESTIONS
}

SKIP_WORDS: List[str] = [
    'следующий вопрос', 'давайте дальше', 'не знаю',
    'пропустить', 'далее', 'next', 'skip'
]

# Константы для системных промптов
SYSTEM_PROMPT = """
Ты профессиональный HR-специалист компании Magenta Technology, проводящий собеседование на позицию {position}. 
Твои задачи:
1. Понять уровень и опыт кандидата. Адаптировать вопросы под уровень кандидата
2. Четко следовать структуре интервью
3. Оценивать полноту ответов
4. Вести диалог естественно и профессионально

Правила:
- Максимальное время прохождение собеседование 10 минут
- Вопросы задавай по одному
- Максимум 1 уточнение на вопрос
- Немедленный переход при уклонении
- Естественная имитация человеческого интервьюера
- Адаптивность и Строгое соответствие уровня вопросов опыту кандидата
"""

SUMMARY_PROMPT = """
Ты профессиональный HR-специалист. На основе всех ответов кандидата по вакансии '{direction}' и его ФИО: {fio}, 
составь подробные итоги собеседования для HR-специалиста. Включи:
1. ФИО кандидата
2. Сильные и слабые стороны
3. Общую рекомендацию
4. Проверку уникальности ответов
5. Вывод о компетенциях.
6. Укажи какие компетенции требуется проверить н аочном собеседовании. Приведи примеры вопросов по каждой компетенции.
7. Если принимаешь решение отказать кандидату напиши вежливо причину отказа, укажи области для развития, которые в будущем помогут успешно пройти собеседование
Пиши кратко, по делу, только на русском языке.
"""


async def ask_gigachat_with_fallback(messages: List[Dict[str, str]]) -> str:
    """Вспомогательная функция для обработки запросов к GigaChat с обработкой ошибок"""
    try:
        resp = gigachat_api.ask_gigachat(messages)
        return resp['choices'][0]['message']['content']
    except Exception as e:
        raise Exception(f"Ошибка при обращении к GigaChat API: {str(e)}")


def is_skip_answer(text: str) -> bool:
    """Проверяет, является ли ответ попыткой пропустить вопрос"""
    text_lower = text.lower()
    return any(word in text_lower for word in SKIP_WORDS)


async def validate_fio(fio: str) -> bool:
    """Проверяет валидность ФИО"""
    parts = fio.split()
    return len(parts) >= 2 and all(len(part) > 1 for part in parts)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await message.answer(
        "Привет! Я HR-бот компании Magenta. Время прохождения тестирования займет 5 минут. "
        "Для начала, пожалуйста, напишите ваши ФИО:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(InterviewStates.waiting_fio)


@router.message(InterviewStates.waiting_fio)
async def get_fio(message: Message, state: FSMContext):
    """Получение и валидация ФИО"""
    fio = message.text.strip()
    if not await validate_fio(fio):
        await message.answer("Пожалуйста, введите ваши фамилию, имя и (при наличии) отчество полностью.")
        return

    await state.update_data(fio=fio)
    await message.answer(
        "Спасибо! Теперь выберите позицию, на которую вы собеседуетесь:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text=dir)] for dir in DIRECTIONS],
            resize_keyboard=True
        )
    )
    await state.set_state(InterviewStates.choosing_direction)


@router.message(InterviewStates.choosing_direction, F.text.in_(DIRECTIONS.keys()))
async def choose_direction(message: Message, state: FSMContext):
    """Обработка выбора направления"""
    direction = message.text
    await state.update_data({
        'direction': direction,
        'q_idx': 0,
        'answers': [],
        'clarify_count': 0
    })
    await message.answer(
        f"Отлично! Начинаем интервью по направлению: {direction}. Желаем удачи!",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await ask_next_question(message, state)


async def ask_next_question(message: Message, state: FSMContext):
    """Задаем следующий вопрос или завершаем интервью"""
    data = await state.get_data()
    direction = data['direction']
    q_idx = data['q_idx']
    questions = DIRECTIONS[direction]

    if q_idx < len(questions):
        await message.answer(questions[q_idx])
        await state.update_data(clarify_count=0)
        await state.set_state(InterviewStates.asking_questions)
    else:
        await summarize_and_send(message, state)


async def process_question_answer(message: Message, state: FSMContext, clarifying: bool = False):
    """Обработка ответа на вопрос (основной или уточняющий)"""
    data = await state.get_data()
    direction = data['direction']
    q_idx = data['q_idx']
    questions = DIRECTIONS[direction]
    answers = data['answers']
    clarify_count = data.get('clarify_count', 0)

    if is_skip_answer(message.text):
        answers.append({"question": questions[q_idx], "answer": message.text})
        await state.update_data(q_idx=q_idx + 1, answers=answers, clarify_count=0)
        await ask_next_question(message, state)
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(position=direction)},
        {"role": "user", "content": message.text}
    ]

    try:
        content = await ask_gigachat_with_fallback(messages)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")
        return

    if 'OK' in content or clarify_count >= 1:
        answers.append({"question": questions[q_idx], "answer": message.text})
        await state.update_data(q_idx=q_idx + 1, answers=answers, clarify_count=0)
        await ask_next_question(message, state)
    else:
        await message.answer(content)
        await state.update_data(clarify_count=clarify_count + 1)
        await state.set_state(InterviewStates.clarifying)


@router.message(InterviewStates.asking_questions)
async def handle_question_answer(message: Message, state: FSMContext):
    """Обработчик ответа на основной вопрос"""
    await process_question_answer(message, state)


@router.message(InterviewStates.clarifying)
async def handle_clarification_answer(message: Message, state: FSMContext):
    """Обработчик ответа на уточняющий вопрос"""
    await process_question_answer(message, state, clarifying=True)


async def summarize_and_send(message: Message, state: FSMContext):
    """Формирование и отправка итогового резюме"""
    data = await state.get_data()
    direction = data['direction']
    answers = data['answers']
    fio = data.get('fio', 'Не указано')

    messages = [
        {"role": "system", "content": SUMMARY_PROMPT.format(direction=direction, fio=fio)},
        {"role": "user", "content": str(answers)}
    ]

    try:
        summary = await ask_gigachat_with_fallback(messages)
    except Exception as e:
        await message.answer(f"Ошибка при формировании резюме: {str(e)}")
        return

    await message.answer("Спасибо за интервью! Ваши ответы отправлены HR. Мы свяжемся с вами в течение 1 дня")
    await message.bot.send_message(
        HR_TELEGRAM_ID,
        f"Резюме по кандидату {fio} на позицию {direction}:\n\n{summary}"
    )
    await state.clear()