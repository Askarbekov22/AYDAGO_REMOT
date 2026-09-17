from aiogram.fsm.state import (
    State,
    StatesGroup
)


class MasterCreateRepairStates(StatesGroup):
    form = State()
    bike_photo = State()
    payment_photo = State()
    confirm = State()