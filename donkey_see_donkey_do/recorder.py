import base64
import json
import math
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Literal, Optional, Tuple, Union

import pyautogui
from apscheduler.schedulers.background import BackgroundScheduler
from PIL import Image
from pydantic import BaseModel, Field
from pynput import keyboard, mouse
from pynput.mouse import Button


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


# might need to refer to https://stackoverflow.com/questions/68746351/using-pydantic-to-deserialize-sublasses-of-a-model
# and https://stackoverflow.com/questions/68044244/parsing-list-of-different-models-with-pydantic
class BaseEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    screenshot: Optional[Union[Image.Image, Path]] = None

    class Config:
        arbitrary_types_allowed = True
        json_loads = model_json_loads
        json_dumps = model_json_dumps


class ScreenshotEvent(BaseEvent):
    screenshot: Union[Image.Image, Path]


class MouseEvent(BaseEvent):
    device: Literal["mouse"] = "mouse"
    location: Tuple[int, int]


class ClickEvent(MouseEvent):
    action: Literal["press", "release"]
    button: str


class ScrollEvent(MouseEvent):
    action: Literal["scroll"] = "scroll"
    scroll: Tuple[int, int]
    last_action_timestamp: datetime = Field(default_factory=datetime.now)

    def update_scroll(self, dx: int, dy: int) -> None:
        old_dx, old_dy = self.scroll
        self.scroll = (old_dx + dx, old_dy + dy)
        self.last_action_timestamp = datetime.now()


KeyType = Union[keyboard.Key, str]


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


class BaseRecorder:
    def __init__(self, take_screenshot: bool = True, screenshot_directory: Optional[Path] = None):
        self.take_screenshot = take_screenshot
        self.screenshot_directory = screenshot_directory

    def get_screenshot(self) -> Optional[Union[Path, Image.Image]]:
        if not self.take_screenshot:
            return None

        screenshot = pyautogui.screenshot()
        if self.screenshot_directory is None:
            return screenshot

        output_filepath = self.screenshot_directory / (datetime.now().isoformat() + ".png")
        screenshot.save(output_filepath)
        return output_filepath

    def __call__(self, *args, **kwargs):
        raise NotImplementedError


class ScreenshotRecorder(BaseRecorder):
    def __init__(
        self,
        take_screenshot: bool = True,
        screenshot_directory: Optional[Path] = None,
        frequency: Union[int, float] = 1,
    ):
        super().__init__(take_screenshot, screenshot_directory)
        self.frequency = frequency

    def __call__(self, previous_events: Events) -> ScreenshotEvent:
        return ScreenshotEvent(screenshot=self.get_screenshot())


class ClickRecorder(BaseRecorder):
    def __call__(self, x: int, y: int, button: Button, is_press: bool, previous_events: Events) -> ClickEvent:
        return ClickEvent(
            action="press" if is_press else "release",
            button=button.name,
            location=(x, y),
            screenshot=self.get_screenshot(),
        )


class ScrollRecorder(BaseRecorder):
    def __init__(
        self, take_screenshot: bool = True, screenshot_directory: Optional[Path] = None, seconds_to_merge: float = 1
    ):
        super().__init__(take_screenshot, screenshot_directory)
        self.seconds_to_merge = seconds_to_merge

    def merge_with_previous_event(self, x: int, y: int, dx: int, dy: int, previous_events: Events) -> bool:
        if len(previous_events) == 0:
            return False

        previous_event = previous_events[-1]
        return (
            isinstance(previous_event, ScrollEvent)
            and previous_event.location == (x, y)
            and (previous_event.scroll[0] == 0 or math.copysign(1, dx) == math.copysign(1, previous_event.scroll[0]))
            and (previous_event.scroll[1] == 0 or math.copysign(1, dy) == math.copysign(1, previous_event.scroll[1]))
            and ((datetime.now() - previous_event.timestamp).total_seconds() < self.seconds_to_merge)
        )

    def __call__(self, x: int, y: int, dx: int, dy: int, previous_events: Events) -> Optional[ScrollEvent]:
        if self.merge_with_previous_event(x, y, dx, dy, previous_events):
            previous_events[-1].update_scroll(dx, dy)
            return

        return ScrollEvent(
            location=(x, y),
            scroll=(dx, dy),
            screenshot=self.get_screenshot(),
        )


class KeyboardRecorder(BaseRecorder):
    def __init__(
        self, take_screenshot: bool = True, screenshot_directory: Optional[Path] = None, seconds_to_merge: float = 1
    ):
        super().__init__(take_screenshot, screenshot_directory)
        self.seconds_to_merge = seconds_to_merge

    def merge_with_previous_event(self, previous_events: Events) -> bool:
        if len(previous_events) == 0:
            return False

        previous_event = previous_events[-1]
        return isinstance(previous_event, KeyboardEvent) and (
            (datetime.now() - previous_event.timestamp).total_seconds() < self.seconds_to_merge
        )

    def __call__(self, key: KeyType, is_press: bool, previous_events: Events) -> Optional[KeyboardEvent]:
        key = key if isinstance(key, keyboard.Key) else str(key)
        if self.merge_with_previous_event(previous_events):
            previous_events[-1].append_action(key, "press" if is_press else "release")
            return

        event = KeyboardEvent(screenshot=self.get_screenshot())
        event.append_action(key, "press" if is_press else "release")
        return event


class Recorder:
    def __init__(
        self,
        record_click=ClickRecorder(),
        record_scroll=ScrollRecorder(),
        record_keyboard=KeyboardRecorder(),
        record_screenshot=ScreenshotRecorder(),
    ):
        self._record_click = record_click
        self._record_scroll = record_scroll
        self._record_keyboard = record_keyboard
        self._record_screenshot = record_screenshot

        self._mouse_listener = None  # type: Optional[mouse.Listener]
        self._keyboard_listener = None  # type: Optional[keyboard.Listener]

        self._screenshot_scheduler = None  # type: Optional[BackgroundScheduler]

        self.recorded_actions = Events()

    def clear_recording(self) -> None:
        self.recorded_actions = Events()

    def _on_click(self, x: int, y: int, button: Button, is_press: bool):
        self.recorded_actions.append(self._record_click(x, y, button, is_press, self.recorded_actions))

    def _on_scroll(self, x: int, y: int, dx, dy):
        result = self._record_scroll(x, y, dx, dy, self.recorded_actions)
        if result is not None:
            self.recorded_actions.append(result)

    def _take_screenshot(self):
        self.recorded_actions.append(self._record_screenshot(self.recorded_actions))

    def _on_key_press(self, key):
        result = self._record_keyboard(key, True, self.recorded_actions)
        if result is not None:
            self.recorded_actions.append(result)

    def _on_key_release(self, key):
        result = self._record_keyboard(key, False, self.recorded_actions)
        if result is not None:
            self.recorded_actions.append(result)

    def record(self) -> None:
        mouse_kwargs = {}

        if self._record_click:
            mouse_kwargs["on_click"] = self._on_click

        if self._record_scroll:
            mouse_kwargs["on_scroll"] = self._on_scroll

        if len(mouse_kwargs) > 0:
            self._mouse_listener = mouse.Listener(**mouse_kwargs)
            self._mouse_listener.start()

        if self._record_keyboard:
            self._keyboard_listener = keyboard.Listener(on_press=self._on_key_press, on_release=self._on_key_release)
            self._keyboard_listener.start()

        if self._record_screenshot is not None:
            self._screenshot_scheduler = BackgroundScheduler()
            self._screenshot_scheduler.add_job(
                self._take_screenshot, "interval", seconds=1 / self._record_screenshot.frequency
            )
            self._screenshot_scheduler.start()

    def stop(self) -> None:
        if self._mouse_listener is not None:
            self._mouse_listener.stop()

        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()

        if self._screenshot_scheduler is not None:
            self._screenshot_scheduler.shutdown()


"""
class Player:
    def __init__(self, recorded_actions: RecordedActions):
        self.recorded_actions = recorded_actions

    def play(self) -> None:
        for action in self.recorded_actions:
            if action["action"] == "screenshot":
                continue
"""
