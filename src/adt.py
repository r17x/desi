# filename: state_adt_strict.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar("T")  # success value type
E = TypeVar("E")  # error value type

@dataclass(frozen=True)
class NotAsked:
    pass

@dataclass(frozen=True)
class InitialLoading:
    pass

@dataclass(frozen=True)
class Loading:
    # No cached value: strictly “loading after a request started”
    pass

@dataclass(frozen=True)
class Success(Generic[T]):
    value: T

@dataclass(frozen=True)
class Failure(Generic[E]):
    error: E

State = Union[NotAsked, InitialLoading, Loading, Success[T], Failure[E]]

def not_asked() -> State[T, E]:
    return NotAsked()

def initial_loading() -> State[T, E]:
    return InitialLoading()

def loading() -> State[T, E]:
    return Loading()

def success(value: T) -> State[T, E]:
    return Success(value)

def failure(error: E) -> State[T, E]:
    return Failure(error)

def render(state: State[T, E]) -> str:
    match state:
        case NotAsked():
            return "Not asked"
        case InitialLoading():
            return "Loading (initial)…"
        case Loading():
            return "Loading…"
        case Success(value=v):
            return f"Success: {v!r}"
        case Failure(error=e):
            return f"Failure: {e!r}"
        case _:
            raise TypeError("Unknown state variant")

if __name__ == "__main__":
    s1: State[int, str] = not_asked()
    s2: State[int, str] = initial_loading()
    s3: State[int, str] = loading()
    s4: State[int, str] = success(1337)
    s5: State[int, str] = failure("Network error")

    for s in (s1, s2, s3, s4, s5):
        print(render(s))

