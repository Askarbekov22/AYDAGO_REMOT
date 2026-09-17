from aiogram.fsm.state import State, StatesGroup


class CompanyRepairStates(StatesGroup):
    form = State()
    bike_photo = State()
    confirm = State()


class ClientRepairStates(StatesGroup):
    form = State()
    bike_photo = State()
    payment_photo = State()
    confirm = State()