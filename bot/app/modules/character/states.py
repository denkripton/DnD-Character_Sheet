from aiogram.fsm.state import State, StatesGroup


class CharacterCreationStates(StatesGroup):
    generation_mode = State()
    generation_method = State()
    generation_result = State()
    name = State()
    race = State()
    spec_class = State()
    stats_method = State()
    stats = State()
    summary = State()
