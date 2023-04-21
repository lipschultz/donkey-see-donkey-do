from typing import List, Union

from pynput import keyboard, mouse

from donkey_see_donkey_do.events import BaseEvent, ClickEvent, Events, KeyboardEvent, ScreenshotEvent, ScrollEvent


class BaseAction:
    def to_python(self, event: BaseEvent) -> Union[str, List[str]]:
        raise NotImplementedError


class ClickAction(BaseAction):
    def replay(
        self, mouse_controller: mouse.Controller, keyboard_controller: keyboard.Controller, max_duration: float
    ) -> None:
        mouse_controller.position = self.location

        if self.action == "press":
            mouse_controller.press(self._pynput_button)
        else:
            mouse_controller.release(self._pynput_button)


class ScrollAction(BaseAction):
    def replay(
        self, mouse_controller: mouse.Controller, keyboard_controller: keyboard.Controller, max_duration: float
    ) -> None:
        scroll_duration = (self.last_action_timestamp - self.timestamp).total_seconds()

        mouse_controller.position = self.location

        if self.action == "press":
            mouse_controller.press(self._pynput_button)
        else:
            mouse_controller.release(self._pynput_button)


class KeyboardAction(BaseAction):
    def to_python(self, event: KeyboardEvent) -> List[str]:
        actions = []
        previous_time = event.timestamp
        for key, action, timestamp in event.key_actions:
            sleep_duration = (timestamp - previous_time).total_seconds()
            if sleep_duration > 0:
                actions.append(f"time.sleep({sleep_duration})")
            previous_time = timestamp

            if action == "press":
                actions.append(f"keyboard.key_press({key!r})")
            elif action == "release":
                actions.append(f"keyboard.key_release({key!r})")
            else:
                raise ValueError(f"Unsupported keyboard action: {action!r}")

        return actions


class StateSnapshotAction(BaseAction):
    pass


class Actions:
    def __init__(
        self,
        click_actor=ClickAction(),
        scroll_actor=ScrollAction(),
        keyboard_actor=KeyboardAction(),
        state_actor=StateSnapshotAction(),
    ):
        self._click_actor = click_actor
        self._scroll_actor = scroll_actor
        self._keyboard_actor = keyboard_actor
        self._state_actor = state_actor

    def event_to_action(self, event: BaseEvent) -> BaseAction:
        if isinstance(event, ClickEvent):
            return self._click_actor
        elif isinstance(event, ScrollEvent):
            return self._scroll_actor
        elif isinstance(event, KeyboardEvent):
            return self._keyboard_actor
        elif isinstance(event, ScreenshotEvent):
            return self._state_actor
        else:
            raise TypeError(f"Unrecognized event type for {event!r}: type={type(event)}")

    def _generate_wait_for_next_event(self, previous_event: BaseEvent, event: BaseEvent) -> List[str]:
        pass

    def to_python(self, events: Events):
        file_contents = [
            "import time",
            "",
            "from pin_the_tale.interaction import Keyboard, Mouse",
            "",
            "",
            "keyboard = Keyboard()",
            "mouse = Mouse()",
            "",
            "",
        ]

        previous_event = None
        for event in events:
            if previous_event is not None:
                event.timestampprevious_event_time
            action = self.event_to_action(event)
            python_action = action.to_python(event)
            if isinstance(python_action, str):
                python_action = [python_action]

            file_contents.extend(python_action)
