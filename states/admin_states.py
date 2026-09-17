from aiogram.fsm.state import (
    State,
    StatesGroup
)


class AdminRepairStates(
    StatesGroup
):
    rejection_reason = State()