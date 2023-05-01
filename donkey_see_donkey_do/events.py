import base64
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Literal, Optional, Tuple, Union

import pyautogui
import pydantic
from PIL import Image
from pin_the_tail.interaction import MouseButton
from pin_the_tail.location import Point
from pydantic import BaseModel, Field
from pynput import keyboard
from pynput import mouse as pynput_mouse

KeyType = Union[keyboard.Key, str]


def model_json_dumps(val, *, default):
    def basic_default(value):
        if isinstance(value, Image.Image):
            buffer = BytesIO()
            value.save(buffer, format="PNG")
            return {
                "donkey_see_donkey_do": None,
                "type": "image",
                "value": base64.b64encode(buffer.getvalue()).decode("ascii"),
            }
        if isinstance(value, keyboard.Key):
            return {"donkey_see_donkey_do": None, "type": "key", "key": value.name}
        return default(value)

    return json.dumps(val, default=basic_default)


def model_json_loads(value):
    def obj_hook(val):
        if "donkey_see_donkey_do" in val:
            if val["type"] == "key":
                val = keyboard.Key[val["key"]]
            elif val["type"] == "image":
                buffer = BytesIO()
                buffer.write(base64.b64decode(val["value"].encode("ascii")))
                val = Image.open(buffer, formats=("PNG",))
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


class BaseMouseEvent(BaseEvent):
    """
    Basic model for mouse events.  In addition to the fields from ``BaseEvent``, it stores the ``device`` as ``"mouse"``
    and the ``location`` of the mouse.
    """

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


class ClickEvent(BaseMouseEvent):
    action: str
    button: MouseButton

    @pydantic.validator("action")
    def action_is_valid_value(cls, value) -> str:
        original_value = value
        value = value.lower()
        if value not in {"press", "release", "click"}:
            raise ValueError(f"action must be 'press', 'release', or 'click'; received {original_value!r}")
        return value

    @pydantic.validator("button", pre=True)
    def button_is_converted_to_mousebutton(cls, value) -> MouseButton:
        print("validating:", value)
        if isinstance(value, MouseButton):
            return value

        button_mapping = {
            pyautogui.LEFT: MouseButton.LEFT,
            "left": MouseButton.LEFT,
            pynput_mouse.Button.left: MouseButton.LEFT,
            pyautogui.MIDDLE: MouseButton.MIDDLE,
            "middle": MouseButton.MIDDLE,
            "center": MouseButton.MIDDLE,
            pynput_mouse.Button.middle: MouseButton.MIDDLE,
            pyautogui.RIGHT: MouseButton.RIGHT,
            "right": MouseButton.RIGHT,
            pynput_mouse.Button.right: MouseButton.RIGHT,
        }
        original_value = value
        if isinstance(value, str):
            value = value.lower()

        try:
            return button_mapping[value]
        except KeyError:
            raise ValueError(f"Unrecognized value for mouse button; received {original_value!r}")

    @property
    def pynput_button(self) -> pynput_mouse.Button:
        return pynput_mouse.Button[self.button.value.lower()]

    @property
    def pyautogui_button(self) -> str:
        return self.button.pyautogui_button


class ScrollEvent(BaseMouseEvent):
    action: Literal["scroll"] = "scroll"
    scroll: Tuple[int, int]


class KeyboardEvent(BaseEvent):
    device: Literal["keyboard"] = "keyboard"
    key: KeyType
    action: Literal["press", "release", "write"]


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
