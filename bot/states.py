from aiogram.fsm.state import State, StatesGroup

class InterviewStates(StatesGroup):
    waiting_fio = State()
    choosing_direction = State()
    asking_questions = State()
    clarifying = State()
    summary = State() 