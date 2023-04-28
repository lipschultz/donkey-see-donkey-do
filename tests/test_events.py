from datetime import datetime
from pathlib import Path

import pytest
from freezegun import freeze_time
from pin_the_tail.interaction import MouseButton
from pin_the_tail.location import Point
from pydantic import ValidationError
from pynput import mouse

from donkey_see_donkey_do import events
from donkey_see_donkey_do.events import PointChange, ScrollChange


class TestStateSnapshotEvent:
    @staticmethod
    def test_sets_device_to_state():
        subject = events.StateSnapshotEvent(screenshot=Path("."), location=(1, 1))

        assert subject.device == "state"

    @staticmethod
    def test_screenshot_is_required():
        with pytest.raises(ValidationError):
            events.StateSnapshotEvent(location=(1, 1))


class TestClickEvent:
    @staticmethod
    def test_sets_device_to_mouse():
        subject = events.ClickEvent(action="press", button="left", location=(1, 1))

        assert subject.device == "mouse"

    @staticmethod
    @pytest.mark.parametrize(
        "mouse_button,expected_instance",
        [("left", mouse.Button.left), ("right", mouse.Button.right), ("middle", mouse.Button.middle)],
    )
    def test_pynput_button_returns_correct_instance_when_valid_string_given(mouse_button, expected_instance):
        subject = events.ClickEvent(action="press", button=mouse_button, location=(1, 1))

        assert subject._pynput_button == expected_instance

    @staticmethod
    @pytest.mark.parametrize(
        "mouse_button,expected_instance",
        [("left", MouseButton.LEFT), ("right", MouseButton.RIGHT), ("middle", MouseButton.MIDDLE)],
    )
    def test_pin_the_tail_button_returns_correct_instance_when_valid_string_given(mouse_button, expected_instance):
        subject = events.ClickEvent(action="press", button=mouse_button, location=(1, 1))

        assert subject.pin_the_tail_button == expected_instance

    @staticmethod
    @pytest.mark.parametrize("action", ("press", "release", "click"))
    def test_action_is_stored(action):
        subject = events.ClickEvent(action=action, button="left", location=(1, 1))

        assert subject.action == action


class TestScrollEvent:
    @staticmethod
    def test_creating_initial_scroll_event():
        frozen_time = datetime(2023, 4, 28, 7, 49, 12)
        with freeze_time(frozen_time):
            subject = events.ScrollEvent(location=(1, 1))
            subject.append_action(5, 7)

        assert subject.device == "mouse"
        assert subject.action == "scroll"
        assert subject.location == Point(1, 1)
        # assert subject.timestamp == frozen_time  # freezegun / pydantic interaction bug: https://github.com/spulec/freezegun/issues/480
        assert subject.scroll_actions == [ScrollChange(PointChange(5, 7), frozen_time)]
