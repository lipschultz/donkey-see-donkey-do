import base64
import itertools
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Literal, Optional, Union

import pyautogui
import pydantic
from PIL import Image
from pin_the_tail.interaction import KeysToPress, MouseButton, SpecialKey
from pin_the_tail.location import Point
from pydantic import BaseModel, Field, PositiveInt
from pynput import keyboard
from pynput import mouse as pynput_mouse

KeyType = Union[str, SpecialKey]


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
        if isinstance(value, SpecialKey):
            return {"donkey_see_donkey_do": None, "type": "key", "key": value.value}
        return default(value)

    return json.dumps(val, default=basic_default)


def model_json_loads(value):
    def obj_hook(val):
        if "donkey_see_donkey_do" in val:
            if val["type"] == "key":
                val = SpecialKey(val["key"])
            elif val["type"] == "image":
                buffer = BytesIO()
                buffer.write(base64.b64decode(val["value"].encode("ascii")))
                val = Image.open(buffer, formats=("PNG",))
            else:
                raise ValueError(f"Unrecognized type: {val['type']}")  # pragma: no cover

        return val

    return json.loads(value, object_hook=obj_hook)


@dataclass(frozen=True)
class PointChange:
    dx: int
    dy: int


class BaseEvent(BaseModel):
    # pylint: disable=too-few-public-methods
    """
    Basic model for events.

    Base event model that stores information shared across all events:
    * ``timestamp`` -- When the event occurred
    * ``screenshot`` -- Optional, a picture of the screen at the time.
    """

    timestamp: datetime = Field(default_factory=datetime.now)
    screenshot: Optional[Union[Image.Image, Path]] = None

    class Config:
        # pylint: disable=too-few-public-methods
        arbitrary_types_allowed = True
        json_loads = model_json_loads
        json_dumps = model_json_dumps


class StateSnapshotEvent(BaseEvent):
    # pylint: disable=too-few-public-methods
    """
    Event representing the general state of the screen, including what the screen currently looks like and the location
    of the mouse.
    """

    device: Literal["state"] = "state"
    screenshot: Union[Image.Image, Path]
    location: Point


class BaseMouseEvent(BaseEvent):
    # pylint: disable=too-few-public-methods
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


class MouseButtonEvent(BaseMouseEvent):
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
        """Get the pynput representation of the button pressed."""
        return pynput_mouse.Button[self.button.value.lower()]

    @property
    def pyautogui_button(self) -> str:
        """Get the pyautogui representation of the button pressed."""
        return self.button.pyautogui_button


class ClickEvent(MouseButtonEvent):
    action: Literal["click"] = "click"
    n_clicks: PositiveInt = 1
    last_timestamp: Optional[datetime] = None

    @classmethod
    def from_mouse_button_event(cls, mouse_button_event: MouseButtonEvent) -> "ClickEvent":
        """Given a mouse button event, create a ClickEvent."""
        return ClickEvent(
            timestamp=mouse_button_event.timestamp,
            screenshot=mouse_button_event.screenshot,
            location=mouse_button_event.location,
            button=mouse_button_event.button,
        )

    @property
    def last_timestamp_or_first(self) -> datetime:
        """Return ``last_timestamp``, or ``timestamp`` if ``last_timestamp`` is ``None``"""
        return self.last_timestamp or self.timestamp

    def update_with(self, other_event: "ClickEvent") -> None:
        """
        Update the current event's:
        - ``n_clicks`` = ``self.n_clicks`` + ``other_event.n_clicks``
        - ``timestamp`` = ``min(self.timestamp, other_event.timestamp)``
        - ``last_timestamp`` = ``max(self.last_timestamp, other_event.timestamp, other_event.last_timestamp)``
        """
        self.n_clicks += other_event.n_clicks
        new_timestamp = min(self.timestamp, other_event.timestamp)

        options_for_last_timestamp = [self.timestamp, other_event.timestamp]
        if self.last_timestamp is not None:
            options_for_last_timestamp.append(self.last_timestamp)
        if other_event.last_timestamp is not None:
            options_for_last_timestamp.append(other_event.last_timestamp)

        self.last_timestamp = max(options_for_last_timestamp)
        self.timestamp = new_timestamp


class ScrollEvent(BaseMouseEvent):
    # pylint: disable=too-few-public-methods
    action: Literal["scroll"] = "scroll"
    scroll: PointChange
    last_timestamp: Optional[datetime] = None

    @property
    def last_timestamp_or_first(self) -> datetime:
        """Return ``last_timestamp``, or ``timestamp`` if ``last_timestamp`` is ``None``"""
        return self.last_timestamp or self.timestamp

    def update_with(self, other_event: "ScrollEvent") -> None:
        """
        Update the current event's:
        - ``scroll`` = ``self.scroll`` + ``other_event.scroll``
        - ``timestamp`` = ``min(self.timestamp, other_event.timestamp)``
        - ``last_timestamp`` = ``max(self.last_timestamp, other_event.timestamp, other_event.last_timestamp)``
        """
        self.scroll = PointChange(self.scroll.dx + other_event.scroll.dx, self.scroll.dy + other_event.scroll.dy)
        new_timestamp = min(self.timestamp, other_event.timestamp)

        options_for_last_timestamp = [self.timestamp, other_event.timestamp]
        if self.last_timestamp is not None:
            options_for_last_timestamp.append(self.last_timestamp)
        if other_event.last_timestamp is not None:
            options_for_last_timestamp.append(other_event.last_timestamp)

        self.last_timestamp = max(options_for_last_timestamp)
        self.timestamp = new_timestamp


class KeyboardEvent(BaseEvent):
    device: Literal["keyboard"] = "keyboard"
    action: Literal["press", "release"]
    key: KeyType

    @property
    def pynput_key(self) -> Union[keyboard.Key, str]:
        """Get the pynput representation of the key pressed."""
        raise NotImplementedError

    @property
    def pyautogui_key(self) -> str:
        """Get the pyautogui representation of the key pressed."""
        if isinstance(self.key, str):
            return self.key
        return self.key.pyautogui_key


class WriteEvent(BaseEvent):
    device: Literal["keyboard"] = "keyboard"
    action: Literal["write"] = "write"
    keys: KeysToPress = Field(default_factory=KeysToPress)
    last_timestamp: Optional[datetime] = None

    @pydantic.validator("keys", pre=True)
    def convert_keys_to_keystopress(cls, value: Union[KeysToPress, KeyType, Iterable[KeyType]]) -> KeysToPress:
        if isinstance(value, (str, SpecialKey)):
            value = [value]

        if not isinstance(value, KeysToPress):
            value = KeysToPress(value)

        return value

    @classmethod
    def from_keyboard_event(cls, keyboard_event: KeyboardEvent) -> "WriteEvent":
        """Given a KeyboardEvent, return a WriteEvent with the same timestamp and key."""
        event = WriteEvent(timestamp=keyboard_event.timestamp, screenshot=keyboard_event.screenshot)
        event.keys.append(keyboard_event.key)
        return event

    @classmethod
    def from_raw_key(cls, key: Union[KeyType, Iterable[KeyType]]) -> "WriteEvent":
        """Create a WriteEvent with the given key or iterable of keys."""
        event = WriteEvent()
        if isinstance(key, (str, SpecialKey)):
            key = [key]
        event.keys.extend(key)
        return event

    @property
    def last_timestamp_or_first(self) -> datetime:
        """Return ``last_timestamp``, or ``timestamp`` if ``last_timestamp`` is ``None``"""
        return self.last_timestamp or self.timestamp

    @property
    def pyautogui_keys(self) -> List[str]:
        """Get the pyautogui representation of the keys pressed."""
        return list(
            itertools.chain.from_iterable(
                list(key) if isinstance(key, str) else [key.pyautogui_key] for key in self.keys
            )
        )

    def append(self, other_event: "WriteEvent") -> None:
        """
        Append ``other_event``'s keys onto the end of the current event's keys.  Additionally, update the timestamps
        based on ``other_event``'s timestamps:
        - ``timestamp`` = ``min(self.timestamp, other_event.timestamp)``
        - ``last_timestamp`` = ``max(self.last_timestamp, other_event.timestamp, other_event.last_timestamp)``
        """
        self.keys.extend(other_event.keys)
        new_timestamp = min(self.timestamp, other_event.timestamp)

        options_for_last_timestamp = [self.timestamp, other_event.timestamp]
        if self.last_timestamp is not None:
            options_for_last_timestamp.append(self.last_timestamp)
        if other_event.last_timestamp is not None:
            options_for_last_timestamp.append(other_event.last_timestamp)

        self.last_timestamp = max(options_for_last_timestamp)
        self.timestamp = new_timestamp


RealEventType = Union[StateSnapshotEvent, ClickEvent, MouseButtonEvent, ScrollEvent, KeyboardEvent, WriteEvent]


class Events(BaseModel):
    __root__: List[RealEventType] = Field(default_factory=list)

    @classmethod
    def from_iterable(cls, iterable: Iterable[RealEventType]) -> "Events":
        """Create an ``Events`` instance from the iterable."""
        return cls(__root__=list(iterable))

    def __len__(self) -> int:
        return len(self.__root__)

    def append(self, item: RealEventType) -> None:
        self.__root__.append(item)

    def extend(self, items: Iterable[RealEventType]) -> None:
        self.__root__.extend(items)

    def __getitem__(self, item: int) -> RealEventType:
        return self.__root__[item]

    def __delitem__(self, key):
        del self.__root__[key]

    def __iter__(self):
        return iter(self.__root__)

    class Config:
        # pylint: disable=too-few-public-methods
        arbitrary_types_allowed = True
        json_loads = model_json_loads
        json_dumps = model_json_dumps
