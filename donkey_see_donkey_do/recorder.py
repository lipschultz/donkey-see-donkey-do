import base64
import json
from datetime import datetime
from io import BytesIO
from typing import List, Literal, Optional, Tuple, Union

import pyautogui
from apscheduler.schedulers.background import BackgroundScheduler
from PIL import Image
from pydantic import BaseModel, Field
from pynput import mouse
from pynput.mouse import Button, Controller


def model_json_dumps(v, *, default):
    def basic_default(value):
        if isinstance(value, Image.Image):
            buffer = BytesIO()
            value.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")
        return default(value)

    return json.dumps(v, default=basic_default)


def model_json_loads(value):
    def obj_hook(val):
        screenshot = val.get("screenshot")
        if screenshot is not None:
            buffer = BytesIO()
            buffer.write(base64.b64decode(screenshot.encode("ascii")))
            val["screenshot"] = Image.open(buffer, formats=("PNG",))
        return val

    return json.loads(value, object_hook=obj_hook)


# might need to refer to https://stackoverflow.com/questions/68746351/using-pydantic-to-deserialize-sublasses-of-a-model
# and https://stackoverflow.com/questions/68044244/parsing-list-of-different-models-with-pydantic
class BaseEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    screenshot: Optional[Image.Image] = None

    class Config:
        arbitrary_types_allowed = True
        json_loads = model_json_loads
        json_dumps = model_json_dumps


class ScreenshotEvent(BaseEvent):
    screenshot: Image.Image


class MouseEvent(BaseEvent):
    device: Literal["mouse"] = "mouse"
    location: Tuple[int, int]


class ClickEvent(MouseEvent):
    action: Literal["press", "release"]
    button: str


class ScrollEvent(MouseEvent):
    action: Literal["scroll"] = "scroll"
    scroll: Tuple[int, int]

    def update_scroll(self, dx: int, dy: int) -> None:
        old_dx, old_dy = self.scroll
        self.scroll = (old_dx + dx, old_dy + dy)


RealEventsType = Union[ScreenshotEvent, ClickEvent, ScrollEvent]


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


class Recorder:
    def __init__(
        self,
        record_click=True,
        record_scroll=True,
        screenshot_on_action=True,
        screenshot_frequency: Optional[Union[float, int]] = None,
    ):
        self._record_click = record_click
        self._record_scroll = record_scroll
        self.screenshot_on_action = screenshot_on_action
        self.screenshot_frequency = screenshot_frequency

        self._mouse_controller = Controller()
        self._mouse_listener = None  # type: Optional[mouse.Listener]

        self._screenshot_scheduler = None  # type: Optional[BackgroundScheduler]

        self.recorded_actions = Events()

    def clear_recording(self) -> None:
        self.recorded_actions = Events()

    def _on_click(self, x: int, y: int, button: Button, is_press: bool):
        self.recorded_actions.append(
            ClickEvent(
                action="press" if is_press else "release",
                button=button.name,
                location=(x, y),
                screenshot=pyautogui.screenshot() if self.screenshot_on_action else None,
            )
        )

    def _on_scroll(self, x: int, y: int, dx, dy):
        if len(self.recorded_actions) > 0:
            last_action = self.recorded_actions[-1]
            if (
                isinstance(last_action, ScrollEvent)
                and last_action.location == (x, y)
                and (datetime.now() - last_action.timestamp).total_seconds() < 1
            ):
                last_action.update_scroll(dx, dy)
                return

        self.recorded_actions.append(
            ScrollEvent(
                location=(x, y),
                scroll=(dx, dy),
                screenshot=pyautogui.screenshot() if self.screenshot_on_action else None,
            )
        )

    def _take_screenshot(self):
        self.recorded_actions.append(ScreenshotEvent(screenshot=pyautogui.screenshot()))

    def record(self) -> None:
        mouse_kwargs = {}

        if self._record_click:
            mouse_kwargs["on_click"] = self._on_click

        if self._record_scroll:
            mouse_kwargs["on_scroll"] = self._on_scroll

        if len(mouse_kwargs) > 0:
            self._mouse_listener = mouse.Listener(**mouse_kwargs)
            self._mouse_listener.start()

        if self.screenshot_frequency:
            self._screenshot_scheduler = BackgroundScheduler()
            self._screenshot_scheduler.add_job(self._take_screenshot, "interval", seconds=1 / self.screenshot_frequency)
            self._screenshot_scheduler.start()

    def stop(self) -> None:
        self._mouse_listener.stop()
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
