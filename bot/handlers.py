from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from bot.states import InterviewStates
from questions.qa import QA_QUESTIONS
from questions.sales import SALES_QUESTIONS
from giga.api import gigachat_api
from config import HR_TELEGRAM_ID

router = Router()

DIRECTIONS = {
    'QA': QA_QUESTIONS,
    'Менеджер по продажам': SALES_QUESTIONS
}

SKIP_WORDS = [
    'следующий вопрос', 'давайте дальше', 'не знаю', 'пропустить', 'далее', 'next', 'skip'
]

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "Привет! Я HR-бот. Время прохождения тестирования займет 5 минут. Для начала, пожалуйста, напишите ваши ФИО:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(InterviewStates.waiting_fio)

@router.message(InterviewStates.waiting_fio)
async def get_fio(message: Message, state: FSMContext):
    fio = message.text.strip()
    if len(fio.split()) < 2:
        await message.answer("Пожалуйста, введите ваши фамилию, имя и (при наличии) отчество полностью.")
        return
    await state.update_data(fio=fio)
    await message.answer(
        "Спасибо! Теперь выберите направление собеседования:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text=dir)] for dir in DIRECTIONS],
            resize_keyboard=True
        )
    )
    await state.set_state(InterviewStates.choosing_direction)

@router.message(InterviewStates.choosing_direction, F.text.in_(DIRECTIONS.keys()))
async def choose_direction(message: Message, state: FSMContext):
    direction = message.text
    await state.update_data(direction=direction, q_idx=0, answers=[], clarifying=False, clarify_count=0)
    await message.answer(f"Отлично! Начинаем интервью по направлению: {direction}. Желаем удачи!", reply_markup=types.ReplyKeyboardRemove())
    await ask_next_question(message, state)

async def ask_next_question(message: Message, state: FSMContext):
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

def is_skip_answer(text: str) -> bool:
    return any(word in text.lower() for word in SKIP_WORDS)

@router.message(InterviewStates.asking_questions)
async def process_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    direction = data['direction']
    q_idx = data['q_idx']
    questions = DIRECTIONS[direction]
    answers = data['answers']
    clarify_count = data.get('clarify_count', 0)
    if is_skip_answer(message.text):
        answers.append({"question": questions[q_idx], "answer": message.text})
        await state.update_data(q_idx=q_idx+1, answers=answers, clarifying=False, clarify_count=0)
        await ask_next_question(message, state)
        return

    system_prompt = (
        "Ты опытный HR-специалист, проводишь собеседование с кандидатом. "
        "Твоя задача — задать вопрос кандидату и оценить его ответ. "
        "Если ответ кандидата неполный, неясный или требует уточнения, задай только один уточняющий вопрос, чтобы получить больше информации. "
        "Если кандидат отвечает уклончиво, пишет 'не знаю', 'давайте дальше', 'следующий вопрос' или что-то подобное, просто переходи к следующему вопросу и не настаивай. "
        "Если ответ кандидата хороший и не требует уточнений, переходи к следующему вопросу. "
        "Максимальное количество уточняющих вопросов по одному основному вопросу — один. Если после одного уточнения ответ всё ещё не ясен, переходи к следующему вопросу. "
        "Не сообщай кандидату, что его ответы анализирует ИИ или программа. "
        "Общайся вежливо, как обычный HR, только на русском языке. "
        "Не повторяй вопрос, не добавляй лишних комментариев. "
        "Вопросы не должны повторяться. "
        "Если всё понятно — просто переходи к следующему вопросу."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message.text}
    ]
    try:
        resp = gigachat_api.ask_gigachat(messages)
        content = resp['choices'][0]['message']['content']
    except Exception as e:
        await message.answer(f"Ошибка AI: {e}")
        return
    if 'OK' in content or clarify_count >= 1:
        answers.append({"question": questions[q_idx], "answer": message.text})
        await state.update_data(q_idx=q_idx+1, answers=answers, clarifying=False, clarify_count=0)
        await ask_next_question(message, state)
    else:
        await message.answer(f"{content}")
        await state.update_data(clarifying=True, clarify_count=clarify_count+1)
        await state.set_state(InterviewStates.clarifying)

@router.message(InterviewStates.clarifying)
async def process_clarification(message: Message, state: FSMContext):
    data = await state.get_data()
    direction = data['direction']
    q_idx = data['q_idx']
    questions = DIRECTIONS[direction]
    answers = data['answers']
    clarify_count = data.get('clarify_count', 0)
    if is_skip_answer(message.text):
        answers.append({"question": questions[q_idx], "answer": message.text})
        await state.update_data(q_idx=q_idx+1, answers=answers, clarifying=False, clarify_count=0)
        await ask_next_question(message, state)
        return

    system_prompt = (
        "Ты опытный HR-специалист, проводишь собеседование с кандидатом. "
        "Твоя задача — задать вопрос кандидату и оценить его ответ. "
        "Если ответ кандидата неполный, неясный или требует уточнения, задай только один уточняющий вопрос, чтобы получить больше информации. "
        "Если кандидат отвечает уклончиво, пишет 'не знаю', 'давайте дальше', 'следующий вопрос' или что-то подобное, просто переходи к следующему вопросу и не настаивай. "
        "Если ответ кандидата хороший и не требует уточнений, переходи к следующему вопросу. "
        "Максимальное количество уточняющих вопросов по одному основному вопросу — один. Если после одного уточнения ответ всё ещё не ясен, переходи к следующему вопросу. "
        "Не сообщай кандидату, что его ответы анализирует ИИ или программа. "
        "Общайся вежливо, как обычный HR, только на русском языке. "
        "Не повторяй вопрос, не добавляй лишних комментариев. "
        "Вопросы не должны повторяться. "
        "Если всё понятно — просто переходи к следующему вопросу."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message.text}
    ]
    try:
        resp = gigachat_api.ask_gigachat(messages)
        content = resp['choices'][0]['message']['content']
    except Exception as e:
        await message.answer(f"Ошибка AI: {e}")
        return
    if 'OK' in content or clarify_count >= 1:
        answers.append({"question": questions[q_idx], "answer": message.text})
        await state.update_data(q_idx=q_idx+1, answers=answers, clarifying=False, clarify_count=0)
        await ask_next_question(message, state)
    else:
        await message.answer(f"{content}")
        await state.update_data(clarify_count=clarify_count+1)
        await state.set_state(InterviewStates.clarifying)

async def summarize_and_send(message: Message, state: FSMContext):
    data = await state.get_data()
    direction = data['direction']
    answers = data['answers']
    fio = data.get('fio', 'Не указано')
    summary_prompt = (
        "Ты профессиональный HR-специалист. "
        f"На основе всех ответов кандидата по вакансии '{direction}' и его ФИО: {fio}, составь подробное резюме для HR-специалиста. "
        "Включи в резюме: ФИО кандидата; сильные и слабые стороны кандидата; общую рекомендацию: подходит ли кандидат для этой вакансии; проверь уникальность ответов кандидата и укажи, использовал ли он интернет при ответах; сделай вывод о компетенциях кандидата на основе его ответов; пиши кратко, по делу, только на русском языке."
    )
    messages = [
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": str(answers)}
    ]
    try:
        resp = gigachat_api.ask_gigachat(messages)
        summary = resp['choices'][0]['message']['content']
    except Exception as e:
        await message.answer(f"Ошибка AI при формировании summary: {e}")
        return
    await message.answer("Спасибо за интервью! Ваши ответы отправлены HR.")
    await message.bot.send_message(HR_TELEGRAM_ID, f"Резюме по кандидату:\n{summary}")
    await state.clear() 