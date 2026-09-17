from aiogram.fsm.state import State, StatesGroup


class RepairRequestStates(StatesGroup):
    bike_number = State()
    payment_status = State()

    amount = State()
    payment_method = State()
    payment_photo = State()

    comment = State()
    confirm = State()