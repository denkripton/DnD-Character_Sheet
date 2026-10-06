from aiogram.fsm.state import State, StatesGroup


class CharacterCreationStates(StatesGroup):
    name = State()
    race = State()
    spec_class = State()
    stats_method = State()
    stats = State()
    summary = State()
