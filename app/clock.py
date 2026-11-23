"""Injectable clock: a callable returning the current naive local datetime."""
from collections.abc import Callable
from datetime import datetime

from fastapi import Request

Clock = Callable[[], datetime]


def system_clock() -> datetime:
    """Default clock: naive local time."""
    return datetime.now()


def get_now(request: Request) -> datetime:
    """FastAPI dependency: current time from the app's own clock."""
    return request.app.state.clock()
