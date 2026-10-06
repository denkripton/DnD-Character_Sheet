from aiogram.fsm.state import State, StatesGroup


class CharacterCreationStates(StatesGroup):
    name = State()
    race = State()
    spec_class = State()
    summary = State()
