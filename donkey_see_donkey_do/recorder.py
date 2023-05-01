from typing import Union

import pyautogui
from apscheduler.schedulers.background import BackgroundScheduler
from PIL import Image
from pynput import keyboard, mouse
from pynput.mouse import Button

from donkey_see_donkey_do.events import ClickEvent, Events, KeyboardEvent, ScrollEvent, StateSnapshotEvent


class Recorder:
    def __init__(self, snapshot_frequency: Union[int, float] = 1):
        self.recorded_events = Events()
        self.snapshot_frequency = snapshot_frequency

        self._mouse_listener = None
        self._keyboard_listener = None
        self._state_snapshot_scheduler = None

    def clear_events(self) -> None:
        self.recorded_events = Events()

    def get_events(self) -> Events:
        return self.recorded_events

    def _get_screenshot(self) -> Image.Image:
        return pyautogui.screenshot()

    def _on_click(self, x: int, y: int, button: Button, is_press: bool):
        event = ClickEvent(
            screenshot=self._get_screenshot(),
            location=(x, y),
            action="press" if is_press else "release",
            button=button.value,
        )
        self.recorded_events.append(event)

    def _on_scroll(self, x: int, y: int, dx, dy):
        event = ScrollEvent(
            screenshot=self._get_screenshot(),
            location=(x, y),
            scroll=(dx, dy),
        )
        self.recorded_events.append(event)

    def _on_key_press(self, key):
        event = KeyboardEvent(
            screenshot=self._get_screenshot(),
            key=key,
            action="press",
        )
        self.recorded_events.append(event)

    def _on_key_release(self, key):
        event = KeyboardEvent(
            screenshot=self._get_screenshot(),
            key=key,
            action="release",
        )
        self.recorded_events.append(event)

    def _take_snapshot(self):
        event = StateSnapshotEvent(
            screenshot=self._get_screenshot(),
            location=pyautogui.position(),
        )
        self.recorded_events.append(event)

    def record(self) -> None:
        self._mouse_listener = mouse.Listener(on_click=self._on_click, on_scroll=self._on_scroll)
        self._mouse_listener.start()

        self._keyboard_listener = keyboard.Listener(on_press=self._on_key_press, on_release=self._on_key_release)
        self._keyboard_listener.start()

        self._state_snapshot_scheduler = BackgroundScheduler()
        self._state_snapshot_scheduler.add_job(self._take_snapshot, "interval", seconds=1 / self.snapshot_frequency)
        self._state_snapshot_scheduler.start()

    def stop(self) -> None:
        if self._mouse_listener is not None:
            self._mouse_listener.stop()

        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()

        if self._state_snapshot_scheduler is not None:
            self._state_snapshot_scheduler.shutdown()
