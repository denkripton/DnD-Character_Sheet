from aiogram.fsm.state import State, StatesGroup


class BackstoryStates(StatesGroup):
    character_saved = State()
    prompt = State()
    review = State()
    edit = State()
