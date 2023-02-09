import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import pyautogui
from apscheduler.schedulers.background import BackgroundScheduler
from PIL import Image
from pynput import mouse
from pynput.mouse import Button, Controller


class RecordedActions:
    def __init__(self):
        self.actions = []

    def __len__(self):
        return len(self.actions)

    def append(self, action: dict) -> None:
        self.actions.append(action)

    @property
    def last_action(self) -> dict:
        return self.actions[-1]

    def __getitem__(self, item: int) -> dict:
        return self.actions[item]

    def _json_encoder(self, value):
        if isinstance(value, Image.Image):
            return value.tobytes().hex()
        if isinstance(value, datetime):
            return value.isoformat()
        else:
            raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")  # pragma: no cover

    def render(self, output_filepath: Union[str, Path]) -> None:
        with open(output_filepath, "w") as fp:
            json.dump(self.actions, fp, default=self._json_encoder)


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

        self._screenshot_scheduler = None  # type: Optional[BaseScheduler]

        self.recorded_actions = RecordedActions()

    def clear_recording(self) -> None:
        self.recorded_actions = RecordedActions()

    def _record_event(self, content: dict, *, take_screenshot: Optional[bool] = None) -> None:
        content = {
            "datetime": datetime.now(),
            **content,
        }
        if take_screenshot is True or (take_screenshot is None and self.screenshot_on_action):
            content["screenshot"] = pyautogui.screenshot()
        self.recorded_actions.append(content)

    def _on_click(self, x: int, y: int, button: Button, is_press: bool):
        self._record_event(
            {
                "device": "mouse",
                "action": "press" if is_press else "release",
                "button": button.name,
                "location": (x, y),
            }
        )

    def _on_scroll(self, x: int, y: int, dx, dy):
        if len(self.recorded_actions) > 0:
            last_action = self.recorded_actions.last_action
            if (
                last_action["action"] == "scroll"
                and last_action["location"] == (x, y)
                and (datetime.now() - last_action["datetime"]).total_seconds() < 1
            ):
                total_dx, total_dy = last_action["scroll"]
                total_dx += dx
                total_dy += dy
                last_action["scroll"] = (total_dx, total_dy)
                return

        self._record_event(
            {
                "device": "mouse",
                "action": "scroll",
                "location": (x, y),
                "scroll": (dx, dy),
            }
        )

    def _take_screenshot(self):
        self._record_event(
            {
                "device": "screen",
                "action": "screenshot",
                "location": self._mouse_controller.position,
            },
            take_screenshot=True,
        )

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
        self._screenshot_scheduler.shutdown()


class Player:
    def __init__(self, recorded_actions: RecordedActions):
        self.recorded_actions = recorded_actions

    def play(self) -> None:
        for action in self.recorded_actions:
            if action["action"] == "screenshot":
                continue
