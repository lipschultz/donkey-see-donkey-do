from dataclasses import dataclass
from typing import Iterable, List

from pydantic import BaseModel, Field

from donkey_see_donkey_do.events import (
    ClickEvent,
    Events,
    MouseButtonEvent,
    MouseMoveEvent,
    RealEventType,
    StateSnapshotEvent,
    model_json_dumps,
    model_json_loads,
)


@dataclass
class Action:
    event: RealEventType
    wait_for: float
    duration: float


class Actions(BaseModel):
    __root__: List[Action] = Field(default_factory=list)

    @classmethod
    def from_iterable(cls, iterable: Iterable[Action]) -> "Actions":
        """Create an ``Actions`` instance from the iterable."""
        return cls(__root__=list(iterable))

    def __len__(self) -> int:
        return len(self.__root__)

    def append(self, item: Action) -> None:
        self.__root__.append(item)

    def extend(self, items: Iterable[Action]) -> None:
        self.__root__.extend(items)

    def __getitem__(self, item: int) -> Action:
        return self.__root__[item]

    def __setitem__(self, key, value: Action):
        self.__root__[key] = value

    def __delitem__(self, key):
        del self.__root__[key]

    def __iter__(self) -> Iterable[Action]:
        return iter(self.__root__)

    class Config:
        # pylint: disable=too-few-public-methods
        arbitrary_types_allowed = True
        json_loads = model_json_loads
        json_dumps = model_json_dumps


def to_actions_using_time(events: Events) -> Actions:
    actions = []
    last_timestamp = None
    for event in events:  # type: RealEventType
        seconds_since_last_event = 0 if last_timestamp is None else (event.timestamp - last_timestamp).total_seconds()
        last_timestamp = event.last_timestamp_or_first

        if isinstance(event, StateSnapshotEvent):
            # This is for mouse movement, which might be inferred from other events
            actions.append(
                Action(event=MouseMoveEvent(location=event.location), wait_for=0, duration=seconds_since_last_event)
            )
            seconds_since_last_event = 0

        if isinstance(event, MouseButtonEvent) and event.action == "click":
            event = ClickEvent.from_mouse_button_event(event)

        if not isinstance(event, StateSnapshotEvent):
            action = Action(event=event, wait_for=seconds_since_last_event, duration=event.duration)
            actions.append(action)

    return Actions.from_iterable(actions)
