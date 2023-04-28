import base64
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Literal, Optional, Tuple, Union

import pydantic
from PIL import Image
from pin_the_tail.interaction import MouseButton
from pin_the_tail.location import Point
from pydantic import BaseModel, Field
from pynput import keyboard, mouse

KeyType = Union[keyboard.Key, str]


def model_json_dumps(val, *, default):
    def basic_default(value):
        if isinstance(value, Image.Image):
            buffer = BytesIO()
            value.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")
        if isinstance(value, keyboard.Key):
            return {"donkey_see_donkey_do": None, "type": "key", "key": value.name}
        return default(value)

    return json.dumps(val, default=basic_default)


def model_json_loads(value):
    def obj_hook(val):
        screenshot = val.get("screenshot")
        if screenshot is not None:
            buffer = BytesIO()
            buffer.write(base64.b64decode(screenshot.encode("ascii")))
            val["screenshot"] = Image.open(buffer, formats=("PNG",))

        if "donkey_see_donkey_do" in val:
            if val["type"] == "key":
                val = keyboard.Key[val["key"]]
            else:
                raise ValueError(f"Unrecognized type: {val['type']}")

        return val

    return json.loads(value, object_hook=obj_hook)


@dataclass(frozen=True)
class PointChange:
    dx: int
    dy: int


@dataclass
class ScrollChange:
    scroll: PointChange
    timestamp: datetime


class BaseEvent(BaseModel):
    """
    Basic model for events.

    Base event model that stores information shared across all events:
    * ``timestamp`` -- When the event occurred
    * ``screenshot`` -- Optional, a picture of the screen at the time.
    """

    timestamp: datetime = Field(default_factory=datetime.now)
    screenshot: Optional[Union[Image.Image, Path]] = None

    class Config:
        arbitrary_types_allowed = True
        json_loads = model_json_loads
        json_dumps = model_json_dumps


class StateSnapshotEvent(BaseEvent):
    """
    Event representing the general state of the screen, including what the screen currently looks like and the location
    of the mouse.
    """

    device: Literal["state"] = "state"
    screenshot: Union[Image.Image, Path]
    location: Point


class MouseEvent(BaseEvent):
    device: Literal["mouse"] = "mouse"
    location: Point

    @pydantic.validator("location")
    def convert_location_to_point(cls, value) -> Point:
        if isinstance(value, (list, tuple)):
            if len(value) == 2:
                value = Point.from_tuple(value)
            else:
                raise ValueError(f"location must be of type Point or a 2-tuple; received {value!r}")

        if not isinstance(value, Point):
            raise TypeError(f"location must be of type Point or a 2-tuple; received {value!r}")

        return value


class ClickEvent(MouseEvent):
    action: Literal["press", "release", "click"]
    button: str

    @property
    def _pynput_button(self) -> mouse.Button:
        return mouse.Button[self.button]

    @property
    def pin_the_tail_button(self) -> MouseButton:
        return MouseButton(self.button)


class ScrollEvent(MouseEvent):
    action: Literal["scroll"] = "scroll"
    scroll_actions: List[ScrollChange] = Field(default_factory=list)

    def append_action(self, dx: int, dy: int) -> None:
        self.scroll_actions.append(ScrollChange(PointChange(dx, dy), datetime.now()))

    @property
    def last_action_timestamp(self) -> datetime:
        return self.scroll_actions[-1].timestamp


class KeyboardEvent(BaseEvent):
    device: Literal["keyboard"] = "keyboard"
    key_actions: List[Tuple[KeyType, Literal["press", "release", "write"], datetime]] = Field(default_factory=list)

    def append_action(self, key: KeyType, action: Literal["press", "release", "write"]) -> None:
        self.key_actions.append((key, action, datetime.now()))


RealEventsType = Union[StateSnapshotEvent, ClickEvent, ScrollEvent, KeyboardEvent]


class Events(BaseModel):
    __root__: List[RealEventsType] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.__root__)

    def append(self, item: RealEventsType) -> None:
        self.__root__.append(item)

    def __getitem__(self, item: int) -> RealEventsType:
        return self.__root__[item]

    class Config:
        arbitrary_types_allowed = True
        json_loads = model_json_loads
        json_dumps = model_json_dumps
