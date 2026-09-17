from aiogram.fsm.state import State, StatesGroup


class MasterRepairStates(StatesGroup):
    form = State()
    bike_photo = State()
    confirm = State()