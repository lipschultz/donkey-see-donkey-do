import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pyautogui
import pytest
from freezegun import freeze_time
from PIL import Image, ImageChops
from pin_the_tail.interaction import MouseButton, SpecialKey
from pin_the_tail.location import Point
from pydantic import ValidationError
from pynput import mouse

from donkey_see_donkey_do import events
from donkey_see_donkey_do.events import PointChange


def assert_timestamp_is_close(event_json, expected_timestamp=None):
    assert "timestamp" in event_json

    if expected_timestamp is None:
        expected_timestamp = datetime.now()
    assert (expected_timestamp - datetime.fromisoformat(event_json["timestamp"])).total_seconds() < 1


def assert_serialized_objects_equal(actual: str, expected: dict):
    actual_dict = json.loads(actual)

    try:
        expected_timestamp = expected.pop("timestamp")
    except KeyError:
        expected_timestamp = None
    assert_timestamp_is_close(actual_dict, expected_timestamp)
    actual_dict.pop("timestamp")

    assert actual_dict == expected


def generate_screenshot() -> Image.Image:
    image = Image.fromarray(np.zeros((25, 50)))
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def generate_screenshot_string() -> str:
    return "iVBORw0KGgoAAAANSUhEUgAAADIAAAAZCAIAAAD8NuoTAAAAG0lEQVR4nO3BMQEAAADCoPVPbQ0PoAAAAODeAA6/AAFIxA5aAAAAAElFTkSuQmCC"


def assert_images_equal(img1, img2):
    # From https://stackoverflow.com/a/68402702
    assert img2.height == img1.height and img2.width == img1.width

    if img2.mode == img1.mode == "RGBA":
        img1_alphas = [pixel[3] for pixel in img2.getdata()]
        img2_alphas = [pixel[3] for pixel in img1.getdata()]
        assert img1_alphas == img2_alphas

    assert not ImageChops.difference(img2.convert("RGB"), img1.convert("RGB")).getbbox()


class TestStateSnapshotEvent:
    @staticmethod
    def test_sets_device_to_state():
        subject = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))

        assert subject.device == "state"

    @staticmethod
    def test_screenshot_is_required():
        with pytest.raises(ValidationError):
            events.StateSnapshotEvent(location=(1, 1))

    @staticmethod
    def test_event_serializes_when_screenshot_is_path():
        subject = events.StateSnapshotEvent(screenshot=Path("."), location=(1, 1))

        actual = subject.json()

        assert_serialized_objects_equal(actual, {"screenshot": ".", "device": "state", "location": {"x": 1, "y": 1}})

    @staticmethod
    def test_deserialize_event_when_screenshot_is_path():
        subject = events.StateSnapshotEvent.parse_raw(
            '{"timestamp": "2023-05-01T10:26:52.625731", "screenshot": ".", "device": "state", "location": {"x": 1, "y": 1}}'
        )

        assert subject == events.StateSnapshotEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"), screenshot=Path("."), location=Point(1, 1)
        )

    @staticmethod
    def test_event_serializes_when_screenshot_is_image():
        subject = events.StateSnapshotEvent(screenshot=generate_screenshot(), location=(1, 1))

        actual = subject.json()

        assert_serialized_objects_equal(
            actual,
            {
                "screenshot": {"donkey_see_donkey_do": None, "type": "image", "value": generate_screenshot_string()},
                "device": "state",
                "location": {"x": 1, "y": 1},
            },
        )

    @staticmethod
    def test_deserialize_event_when_screenshot_is_image():
        json_value = (
            '{"timestamp": "2023-05-01T10:26:52.625731", "screenshot": {"donkey_see_donkey_do": null, "type": "image", "value": "'
            + generate_screenshot_string()
            + '"}, "device": "state", "location": {"x": 1, "y": 1}}'
        )
        subject = events.StateSnapshotEvent.parse_raw(json_value)

        expected = events.StateSnapshotEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"),
            screenshot=generate_screenshot(),
            location=Point(1, 1),
        )

        assert_images_equal(subject.screenshot, expected.screenshot)
        subject.screenshot = Path(".")
        expected.screenshot = Path(".")
        assert subject == expected


class TestClickEvent:
    @staticmethod
    def test_sets_device_to_mouse():
        subject = events.ClickEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))

        assert subject.device == "mouse"

    @staticmethod
    @pytest.mark.parametrize(
        "mouse_button",
        [button for button in MouseButton],
    )
    def test_pin_the_tail_mouse_button_stored_correctly(mouse_button):
        subject = events.ClickEvent(action="press", button=mouse_button, location=Point(1, 1))

        assert subject.button == mouse_button

    @staticmethod
    @pytest.mark.parametrize(
        "mouse_button,expected_instance",
        [
            (mouse.Button.left, MouseButton.LEFT),
            (mouse.Button.middle, MouseButton.MIDDLE),
            (mouse.Button.right, MouseButton.RIGHT),
        ],
    )
    def test_pynput_button_stored_correctly(mouse_button, expected_instance):
        subject = events.ClickEvent(action="press", button=mouse_button, location=Point(1, 1))

        assert subject.button == expected_instance

    @staticmethod
    @pytest.mark.parametrize(
        "mouse_button,expected_instance",
        [
            (pyautogui.LEFT, MouseButton.LEFT),
            (pyautogui.MIDDLE, MouseButton.MIDDLE),
            (pyautogui.RIGHT, MouseButton.RIGHT),
        ],
    )
    def test_pyautogui_button_stored_correctly(mouse_button, expected_instance):
        subject = events.ClickEvent(action="press", button=mouse_button, location=Point(1, 1))

        assert subject.button == expected_instance

    @staticmethod
    @pytest.mark.parametrize(
        "mouse_button",
        ["leftmore", "right with extra stuff", 1, "not a button name at all"],
    )
    def test_invalid_button_raises_validation_error(mouse_button):
        with pytest.raises(ValidationError):
            events.ClickEvent(action="press", button=mouse_button, location=Point(1, 1))

    @staticmethod
    @pytest.mark.parametrize(
        "mouse_button,expected_instance",
        [
            (MouseButton.LEFT, mouse.Button.left),
            (MouseButton.RIGHT, mouse.Button.right),
            (MouseButton.MIDDLE, mouse.Button.middle),
        ],
    )
    def test_pynput_button_returns_correct_instance_when_valid_string_given(mouse_button, expected_instance):
        subject = events.ClickEvent(action="press", button=mouse_button, location=Point(1, 1))

        assert subject.pynput_button == expected_instance

    @staticmethod
    @pytest.mark.parametrize(
        "mouse_button,expected_instance",
        [
            (MouseButton.LEFT, pyautogui.LEFT),
            (MouseButton.RIGHT, pyautogui.RIGHT),
            (MouseButton.MIDDLE, pyautogui.MIDDLE),
        ],
    )
    def test_pin_the_tail_button_returns_correct_instance_when_valid_string_given(mouse_button, expected_instance):
        subject = events.ClickEvent(action="press", button=mouse_button, location=Point(1, 1))

        assert subject.pyautogui_button == expected_instance

    @staticmethod
    @pytest.mark.parametrize("action", ("press", "release", "click"))
    def test_valid_actions_are_stored(action):
        subject = events.ClickEvent(action=action, button="left", location=Point(1, 1))

        assert subject.action == action

    @staticmethod
    @pytest.mark.parametrize("action", ("invalid", "pressmore", "press with other stuff", 1))
    def test_error_raised_when_action_is_not_valid(action):
        with pytest.raises(ValidationError):
            events.ClickEvent(action=action, button="left", location=(1, 1))

    @staticmethod
    def test_event_serializes():
        subject = events.ClickEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))

        actual = subject.json()

        assert_serialized_objects_equal(
            actual,
            {
                "screenshot": None,
                "device": "mouse",
                "action": "release",
                "button": "left",
                "location": {"x": 1, "y": 1},
            },
        )

    @staticmethod
    def test_deserialize_event():
        subject = events.ClickEvent.parse_raw(
            '{"timestamp": "2023-05-01T10:26:52.625731", "screenshot": null, "device": "mouse", "action": "release", "button": "left", "location": {"x": 1, "y": 1}}'
        )

        assert subject == events.ClickEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"),
            action="release",
            button=MouseButton.LEFT,
            location=Point(1, 1),
        )


class TestScrollEvent:
    @staticmethod
    def test_event_serializes():
        subject = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))

        actual = subject.json()

        assert_serialized_objects_equal(
            actual,
            {
                "screenshot": None,
                "device": "mouse",
                "action": "scroll",
                "location": {"x": 1, "y": 1},
                "scroll": {"dx": -2, "dy": 5},
            },
        )

    @staticmethod
    def test_deserialize_event():
        subject = events.ScrollEvent.parse_raw(
            '{"timestamp": "2023-05-01T10:26:52.625731", "screenshot": null, "device": "mouse", "action": "scroll", "location": {"x": 1, "y": 1}, "scroll": {"dx": -2, "dy": 5}}'
        )

        assert subject == events.ScrollEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"),
            action="scroll",
            location=Point(1, 1),
            scroll=PointChange(-2, 5),
        )

    @staticmethod
    def test_creating_scroll_event():
        frozen_time = datetime(2023, 4, 28, 7, 49, 12)
        with freeze_time(frozen_time):
            subject = events.ScrollEvent(location=(1, 1), scroll=(5, 7))

        assert subject.device == "mouse"
        assert subject.action == "scroll"
        assert subject.location == Point(1, 1)
        # assert subject.timestamp == frozen_time  # freezegun / pydantic interaction bug: https://github.com/spulec/freezegun/issues/480
        assert subject.scroll == PointChange(5, 7)


class TestKeyboardEvent:
    @staticmethod
    @pytest.mark.parametrize("character", ["a", "A", "1", ".", "\t"])
    @pytest.mark.parametrize("action", ["press", "release", "write"])
    def test_creating_keyboard_event_with_character_key(character, action):
        subject = events.KeyboardEvent(action=action, key=character)

        assert subject.device == "keyboard"
        assert subject.action == action
        assert subject.key == character

    @staticmethod
    @pytest.mark.parametrize("key", [SpecialKey.ALT, SpecialKey.MULTIPLY, SpecialKey.OPTION])
    @pytest.mark.parametrize("action", ["press", "release", "write"])
    def test_creating_keyboard_event_with_special_key(key, action):
        subject = events.KeyboardEvent(action=action, key=key)

        assert subject.device == "keyboard"
        assert subject.action == action
        assert subject.key == key

    @staticmethod
    @pytest.mark.parametrize("key", [SpecialKey.ALT, "a"])
    def test_event_serializes(key):
        subject = events.KeyboardEvent(action="press", key=key)

        actual = subject.json()

        assert_serialized_objects_equal(
            actual,
            {
                "screenshot": None,
                "device": "keyboard",
                "action": "press",
                "key": key if isinstance(key, str) else {"donkey_see_donkey_do": None, "type": "key", "key": key.value},
            },
        )

    @staticmethod
    @pytest.mark.parametrize("key", [SpecialKey.ALT, "a"])
    def test_deserialize_event(key):
        if isinstance(key, str):
            json_key_field = f'"{key}"'
        else:
            json_key_field = f'{{"donkey_see_donkey_do": null, "type": "key", "key": "{key.value}"}}'

        subject = events.KeyboardEvent.parse_raw(
            f"{{"
            f'"timestamp": "2023-05-01T10:26:52.625731", '
            f'"screenshot": null, '
            f'"device": "keyboard", '
            f'"action": "press", '
            f'"key": {json_key_field}'
            f"}}"
        )

        assert subject == events.KeyboardEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"),
            action="press",
            key=key,
        )
