import base64
import itertools
import json
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Literal, Optional, Union, Any, Dict

import pyautogui
import pydantic
from PIL import Image
from pin_the_tail.interaction import Keyboard, KeysToPress, Mouse, MouseButton, SpecialKey
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

    @property
    def last_timestamp_or_first(self) -> datetime:
        """Return ``timestamp``"""
        return self.timestamp

    @property
    def duration(self) -> float:
        return (self.last_timestamp_or_first - self.timestamp).total_seconds()

    def replay(self, duration: float = 0) -> None:
        raise NotImplementedError

    def _map_for_str(self) -> Dict[str, Any]:
        mapping = {"timestamp": self.timestamp.isoformat()}
        if isinstance(self.screenshot, Image.Image):
            mapping["screenshot"] = "<image>"
        else:
            mapping["screenshot"] = str(self.screenshot)
        return mapping

    def __str__(self):
        return f"{self.__class__.__name__}({', '.join(f'{key}={value}' for key, value in sorted(self._map_for_str().items()))})"

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

    def _map_for_str(self) -> Dict[str, Any]:
        mapping = super()._map_for_str()
        mapping["device"] = self.device
        mapping["location"] = str(self.location)
        return mapping


class BaseMouseEvent(BaseEvent):
    # pylint: disable=too-few-public-methods
    """
    Basic model for mouse events.  In addition to the fields from ``BaseEvent``, it stores the ``device`` as ``"mouse"``
    and the ``location`` of the mouse.
    """

    device: Literal["mouse"] = "mouse"
    location: Point

    def _map_for_str(self) -> Dict[str, Any]:
        mapping = super()._map_for_str()
        mapping["device"] = self.device
        mapping["location"] = str(self.location)
        return mapping

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

    def _replay_move_mouse(self, duration: float):
        Mouse().move_to(self.location, duration=duration)


class MouseMoveEvent(BaseMouseEvent):
    action: Literal["move"] = "move"

    def _map_for_str(self) -> Dict[str, Any]:
        mapping = super()._map_for_str()
        mapping["action"] = self.action
        return mapping

    def replay(self, duration: float = 0) -> None:
        self._replay_move_mouse(duration)


class MouseButtonEvent(BaseMouseEvent):
    action: str
    button: MouseButton

    def _map_for_str(self) -> Dict[str, Any]:
        mapping = super()._map_for_str()
        mapping["action"] = self.action
        mapping["button"] = str(self.button)
        return mapping

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

    def replay(self, duration: float = 0) -> None:
        self._replay_move_mouse(duration)
        mouse = Mouse()
        if self.action == "press":
            mouse.button_press(self.button)
        elif self.action == "release":
            mouse.button_release(self.button)
        elif self.action == "click":
            mouse.click(self.button, 1)


class ClickEvent(MouseButtonEvent):
    action: Literal["click"] = "click"
    n_clicks: PositiveInt = 1
    last_timestamp: Optional[datetime] = None

    @classmethod
    def from_mouse_button_event(cls, mouse_button_event: MouseButtonEvent) -> "ClickEvent":
        """Given a mouse button event, create a ClickEvent."""
        if isinstance(mouse_button_event, ClickEvent):
            return mouse_button_event.copy()
        return ClickEvent(
            timestamp=mouse_button_event.timestamp,
            screenshot=mouse_button_event.screenshot,
            location=mouse_button_event.location,
            button=mouse_button_event.button,
        )

    def _map_for_str(self) -> Dict[str, Any]:
        mapping = super()._map_for_str()
        mapping["n_clicks"] = self.n_clicks
        mapping["last_timestamp"] = self.last_timestamp.isoformat() if self.last_timestamp else None
        return mapping

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

    def replay(self, duration: float = 0) -> None:
        self._replay_move_mouse(duration)
        mouse = Mouse()
        mouse.click(self.button, self.n_clicks)  # FIXME: self.duration should be used to determine the click speed


class ScrollEvent(BaseMouseEvent):
    # pylint: disable=too-few-public-methods
    action: Literal["scroll"] = "scroll"
    scroll: PointChange
    last_timestamp: Optional[datetime] = None

    def _map_for_str(self) -> Dict[str, Any]:
        mapping = super()._map_for_str()
        mapping["scroll"] = self.scroll
        mapping["last_timestamp"] = self.last_timestamp.isoformat() if self.last_timestamp else None
        return mapping

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

    def replay(self, duration: float = 0) -> None:
        self._replay_move_mouse(duration)
        mouse = Mouse()
        # FIXME: self.duration should be used to determine the scroll speed
        # FIXME: this scrolling would, ideally, be done in parallel but should be interleaved
        mouse.scroll_horizontal(self.scroll.dx)
        mouse.scroll_vertical(self.scroll.dy)


class KeyboardEvent(BaseEvent):
    device: Literal["keyboard"] = "keyboard"
    action: Literal["press", "release"]
    key: KeyType

    @pydantic.validator("key", pre=True)
    def key_is_converted_to_keytype(cls, value) -> KeyType:
        if isinstance(value, (str, SpecialKey)):
            return value

        if isinstance(value, keyboard.Key):
            key_to_specialkey = {
                keyboard.Key.alt: SpecialKey.ALT,
                keyboard.Key.alt_l: SpecialKey.ALT_LEFT,
                keyboard.Key.alt_r: SpecialKey.ALT_RIGHT,
                # #: The AltGr key. This is a modifier.
                # alt_gr = 0
                keyboard.Key.backspace: SpecialKey.BACKSPACE,
                keyboard.Key.caps_lock: SpecialKey.CAPS_LOCK,
                #: The command button. On *PC* platforms, this corresponds to the
                #: Super key or Windows key, and on *Mac* it corresponds to the Command
                #: key. This may be a modifier.
                keyboard.Key.cmd: SpecialKey.WIN,
                keyboard.Key.cmd_l: SpecialKey.WIN_LEFT,
                keyboard.Key.cmd_r: SpecialKey.WIN_RIGHT,
                keyboard.Key.ctrl: SpecialKey.CTRL,
                keyboard.Key.ctrl_l: SpecialKey.CTRL_LEFT,
                keyboard.Key.ctrl_r: SpecialKey.CTRL_RIGHT,
                keyboard.Key.delete: SpecialKey.DELETE,
                keyboard.Key.down: SpecialKey.DOWN,
                keyboard.Key.end: SpecialKey.END,
                keyboard.Key.enter: SpecialKey.ENTER,
                keyboard.Key.esc: SpecialKey.ESC,
                keyboard.Key.f1: SpecialKey.F1,
                keyboard.Key.f2: SpecialKey.F2,
                keyboard.Key.f3: SpecialKey.F3,
                keyboard.Key.f4: SpecialKey.F4,
                keyboard.Key.f5: SpecialKey.F5,
                keyboard.Key.f6: SpecialKey.F6,
                keyboard.Key.f7: SpecialKey.F7,
                keyboard.Key.f8: SpecialKey.F8,
                keyboard.Key.f9: SpecialKey.F9,
                keyboard.Key.f10: SpecialKey.F10,
                keyboard.Key.f11: SpecialKey.F11,
                keyboard.Key.f12: SpecialKey.F12,
                keyboard.Key.f13: SpecialKey.F13,
                keyboard.Key.f14: SpecialKey.F14,
                keyboard.Key.f15: SpecialKey.F15,
                keyboard.Key.f16: SpecialKey.F16,
                keyboard.Key.f17: SpecialKey.F17,
                keyboard.Key.f18: SpecialKey.F18,
                keyboard.Key.f19: SpecialKey.F19,
                keyboard.Key.f20: SpecialKey.F20,
                keyboard.Key.home: SpecialKey.HOME,
                keyboard.Key.left: SpecialKey.LEFT,
                keyboard.Key.page_down: SpecialKey.PAGE_DOWN,
                keyboard.Key.page_up: SpecialKey.PAGE_UP,
                keyboard.Key.right: SpecialKey.RIGHT,
                keyboard.Key.shift: SpecialKey.SHIFT,
                keyboard.Key.shift_l: SpecialKey.SHIFT_LEFT,
                keyboard.Key.shift_r: SpecialKey.SHIFT_RIGHT,
                keyboard.Key.space: SpecialKey.SPACE,
                keyboard.Key.tab: SpecialKey.TAB,
                keyboard.Key.up: SpecialKey.UP,
                keyboard.Key.media_play_pause: SpecialKey.PLAY_PAUSE,
                keyboard.Key.media_volume_mute: SpecialKey.VOLUME_MUTE,
                keyboard.Key.media_volume_down: SpecialKey.VOLUME_DOWN,
                keyboard.Key.media_volume_up: SpecialKey.VOLUME_UP,
                keyboard.Key.media_previous: SpecialKey.PREV_TRACK,
                # keyboard.Key.media_next: SpecialKey.NEXT_TRACK,
                keyboard.Key.insert: SpecialKey.INSERT,
                #: The Menu key. This may be undefined for some platforms.
                # keyboard.Key.menu: SpecialKey.,
                keyboard.Key.num_lock: SpecialKey.NUM_LOCK,
                keyboard.Key.pause: SpecialKey.PAUSE,
                keyboard.Key.print_screen: SpecialKey.PRINT_SCREEN,
                keyboard.Key.scroll_lock: SpecialKey.SCROLL_LOCK,
            }
            try:
                return key_to_specialkey[value]
            except KeyError:
                raise ValueError(f"Unrecognized value for key; received {value!r}")
        raise ValueError(f"Unrecognized value for key; received {value!r}")

    def _map_for_str(self) -> Dict[str, Any]:
        mapping = super()._map_for_str()
        mapping["device"] = self.device
        mapping["action"] = self.action
        mapping["key"] = self.key
        return mapping

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

    def replay(self, duration: float = 0) -> None:
        if self.action == "press":
            Keyboard().key_press(self.key)
        else:
            Keyboard().key_press(self.key)


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

    def _map_for_str(self) -> Dict[str, Any]:
        mapping = super()._map_for_str()
        mapping["device"] = self.device
        mapping["action"] = self.action
        mapping["keys"] = self.keys
        mapping["last_timestamp"] = self.last_timestamp.isoformat() if self.last_timestamp else None
        return mapping

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

    def update_with(self, other_event: "WriteEvent") -> None:
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

    def replay(self, duration: float = 0) -> None:
        self.keys.write(len(self.keys) / duration)


RealEventType = Union[
    StateSnapshotEvent, ClickEvent, MouseMoveEvent, MouseButtonEvent, ScrollEvent, KeyboardEvent, WriteEvent
]


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

    def __setitem__(self, key, value: RealEventType):
        self.__root__[key] = value

    def __delitem__(self, key):
        del self.__root__[key]

    def __iter__(self):
        return iter(self.__root__)

    def to_string(self) -> str:
        return "[\n" + "\n".join(f" {i:3d}" + str(event) for i, event in enumerate(self)) + "\n]"

    def to_json(self, filepath: Union[str, Path]):
        with open(filepath, "w") as fp:
            fp.write(self.json())

    @classmethod
    def from_json(cls, filepath: Union[str, Path]) -> "Events":


    class Config:
        # pylint: disable=too-few-public-methods
        arbitrary_types_allowed = True
        json_loads = model_json_loads
        json_dumps = model_json_dumps
