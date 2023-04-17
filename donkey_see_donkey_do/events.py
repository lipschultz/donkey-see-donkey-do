import base64
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Literal, Optional, Tuple, Union

from PIL import Image
from pydantic import BaseModel, Field
from pynput import keyboard, mouse

KeyType = Union[keyboard.Key, str]


def model_json_dumps(v, *, default):
    def basic_default(value):
        if isinstance(value, Image.Image):
            buffer = BytesIO()
            value.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")
        if isinstance(value, keyboard.Key):
            return {"donkey_see_donkey_do": None, "type": "key", "key": value.name}
        return default(value)

    return json.dumps(v, default=basic_default)


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


PointType = Tuple[int, int]


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

    def replay(
        self, mouse_controller: mouse.Controller, keyboard_controller: keyboard.Controller, max_duration: float
    ) -> None:
        raise NotImplementedError


class ScreenshotEvent(BaseEvent):
    """Event representing the general state of the screen."""

    device: Literal["screen"] = "screen"
    screenshot: Union[Image.Image, Path]
    location: PointType


class MouseEvent(BaseEvent):
    device: Literal["mouse"] = "mouse"
    location: PointType


class ClickEvent(MouseEvent):
    action: Literal["press", "release"]
    button: str

    @property
    def _pynput_button(self) -> mouse.Button:
        return mouse.Button[self.button]

    def replay(
        self, mouse_controller: mouse.Controller, keyboard_controller: keyboard.Controller, max_duration: float
    ) -> None:
        mouse_controller.position = self.location

        if self.action == "press":
            mouse_controller.press(self._pynput_button)
        else:
            mouse_controller.release(self._pynput_button)


class ScrollEvent(MouseEvent):
    action: Literal["scroll"] = "scroll"
    scroll: Tuple[int, int]
    last_action_timestamp: datetime = Field(default_factory=datetime.now)

    def update_scroll(self, dx: int, dy: int) -> None:
        old_dx, old_dy = self.scroll
        self.scroll = (old_dx + dx, old_dy + dy)
        self.last_action_timestamp = datetime.now()

    def replay(
        self, mouse_controller: mouse.Controller, keyboard_controller: keyboard.Controller, max_duration: float
    ) -> None:
        scroll_duration = (self.last_action_timestamp - self.timestamp).total_seconds()

        mouse_controller.position = self.location

        if self.action == "press":
            mouse_controller.press(self._pynput_button)
        else:
            mouse_controller.release(self._pynput_button)


class KeyboardEvent(BaseEvent):
    device: Literal["keyboard"] = "keyboard"
    key_actions: List[Tuple[KeyType, Literal["press", "release"], datetime]] = Field(default_factory=list)

    def append_action(self, key: KeyType, action: Literal["press", "release"]) -> None:
        self.key_actions.append((key, action, datetime.now()))


RealEventsType = Union[ScreenshotEvent, ClickEvent, ScrollEvent, KeyboardEvent]


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
