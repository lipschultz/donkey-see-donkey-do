import json
from datetime import datetime
from pathlib import Path
from typing import Union

import numpy as np
import pyautogui
import pytest
from freezegun import freeze_time
from hypothesis import given, strategies
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


def assert_serialized_objects_equal(actual: str, expected: Union[dict, list]):
    actual_parsed = json.loads(actual)

    if isinstance(expected, list):
        assert isinstance(actual_parsed, list)
        assert len(actual_parsed) == len(expected)
        for actual_element, expected_element in zip(actual_parsed, expected):
            assert_serialized_objects_equal(json.dumps(actual_element), expected_element)
    else:
        try:
            expected_timestamp = expected.pop("timestamp")
        except KeyError:
            expected_timestamp = None
        assert_timestamp_is_close(actual_parsed, expected_timestamp)
        actual_parsed.pop("timestamp")

        assert actual_parsed == expected


def generate_screenshot() -> Image.Image:
    image = Image.fromarray(np.zeros((25, 50)))
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def generate_screenshot_string() -> str:
    return (
        "iVBORw0KGgoAAAANSUhEUgAAADIAAAAZCAIAAAD8NuoTAAAAG0lEQVR4nO3BMQEAAADCoPVPbQ0PoAAAAODeAA6/AAFIxA5aAAAAAElFT"
        "kSuQmCC"
    )


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
            json.dumps(
                {
                    "timestamp": "2023-05-01T10:26:52.625731",
                    "screenshot": ".",
                    "device": "state",
                    "location": {"x": 1, "y": 1},
                }
            )
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
        json_value = json.dumps(
            {
                "timestamp": "2023-05-01T10:26:52.625731",
                "screenshot": {"donkey_see_donkey_do": None, "type": "image", "value": generate_screenshot_string()},
                "device": "state",
                "location": {"x": 1, "y": 1},
            }
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


class TestMouseButtonEvent:
    @staticmethod
    def test_sets_device_to_mouse():
        subject = events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))

        assert subject.device == "mouse"

    @staticmethod
    @pytest.mark.parametrize("mouse_button", list(MouseButton))
    def test_pin_the_tail_mouse_button_stored_correctly(mouse_button):
        subject = events.MouseButtonEvent(action="press", button=mouse_button, location=Point(1, 1))

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
        subject = events.MouseButtonEvent(action="press", button=mouse_button, location=Point(1, 1))

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
        subject = events.MouseButtonEvent(action="press", button=mouse_button, location=Point(1, 1))

        assert subject.button == expected_instance

    @staticmethod
    @pytest.mark.parametrize(
        "mouse_button",
        ["leftmore", "right with extra stuff", 1, "not a button name at all"],
    )
    def test_invalid_button_raises_validation_error(mouse_button):
        with pytest.raises(ValidationError):
            events.MouseButtonEvent(action="press", button=mouse_button, location=Point(1, 1))

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
        subject = events.MouseButtonEvent(action="press", button=mouse_button, location=Point(1, 1))

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
        subject = events.MouseButtonEvent(action="press", button=mouse_button, location=Point(1, 1))

        assert subject.pyautogui_button == expected_instance

    @staticmethod
    @pytest.mark.parametrize("action", ("press", "release", "click"))
    def test_valid_actions_are_stored(action):
        subject = events.MouseButtonEvent(action=action, button="left", location=Point(1, 1))

        assert subject.action == action

    @staticmethod
    @pytest.mark.parametrize("action", ("invalid", "pressmore", "press with other stuff", 1))
    def test_error_raised_when_action_is_not_valid(action):
        with pytest.raises(ValidationError):
            events.MouseButtonEvent(action=action, button="left", location=(1, 1))

    @staticmethod
    def test_event_serializes():
        subject = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))

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
        subject = events.MouseButtonEvent.parse_raw(
            json.dumps(
                {
                    "timestamp": "2023-05-01T10:26:52.625731",
                    "screenshot": None,
                    "device": "mouse",
                    "action": "release",
                    "button": "left",
                    "location": {"x": 1, "y": 1},
                }
            )
        )

        assert subject == events.MouseButtonEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"),
            action="release",
            button=MouseButton.LEFT,
            location=Point(1, 1),
        )


class TestClickEvent:
    @staticmethod
    def test_creating_event_with_action_not_click_raises_validation_error():
        with pytest.raises(ValidationError):
            events.ClickEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))

    @staticmethod
    def test_default_number_of_clicks_is_one():
        subject = events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1))

        assert subject.n_clicks == 1

    @staticmethod
    @pytest.mark.parametrize("value", [0, -1])
    def test_value_error_raised_when_n_clicks_is_not_greater_than_0(value):
        with pytest.raises(ValueError):
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1), n_clicks=value)

    @staticmethod
    @given(strategies.integers(1))
    def test_positive_integer_n_clicks_is_accepted(value):
        subject = events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1), n_clicks=value)

        assert subject.n_clicks == value

    @staticmethod
    def test_creating_click_event_from_mouse_button_click_event_uses_all_fields():
        button_event = events.MouseButtonEvent(button=MouseButton.LEFT, location=Point(1, 2), action="click")

        subject = events.ClickEvent.from_mouse_button_event(button_event)

        for field in events.MouseButtonEvent.__fields__:
            assert getattr(button_event, field) == getattr(subject, field)

    @staticmethod
    @pytest.mark.parametrize("action", ["press", "release"])
    def test_creating_click_event_from_mouse_button_event_where_action_not_click_raises_value_error(action):
        button_event = events.MouseButtonEvent(button=MouseButton.LEFT, location=Point(1, 2), action=action)

        with pytest.raises(ValueError):
            events.ClickEvent.from_mouse_button_event(button_event)

    @staticmethod
    def test_event_serializes():
        subject = events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1))

        actual = subject.json()

        assert_serialized_objects_equal(
            actual,
            {
                "screenshot": None,
                "device": "mouse",
                "action": "click",
                "button": "left",
                "location": {"x": 1, "y": 1},
                "n_clicks": 1,
            },
        )

    @staticmethod
    def test_deserialize_event():
        subject = events.ClickEvent.parse_raw(
            json.dumps(
                {
                    "timestamp": "2023-05-01T10:26:52.625731",
                    "screenshot": None,
                    "device": "mouse",
                    "action": "click",
                    "button": "left",
                    "location": {"x": 1, "y": 1},
                    "n_clicks": 3,
                }
            )
        )

        assert subject == events.ClickEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"),
            button=MouseButton.LEFT,
            location=Point(1, 1),
            n_clicks=3,
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
            json.dumps(
                {
                    "timestamp": "2023-05-01T10:26:52.625731",
                    "screenshot": None,
                    "device": "mouse",
                    "action": "scroll",
                    "location": {"x": 1, "y": 1},
                    "scroll": {"dx": -2, "dy": 5},
                }
            )
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
        assert subject.scroll == PointChange(5, 7)
        # freezegun / pydantic interaction bug: https://github.com/spulec/freezegun/issues/480
        # assert subject.timestamp == frozen_time


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
            json_key_field = key
        else:
            json_key_field = {"donkey_see_donkey_do": None, "type": "key", "key": key.value}

        subject = events.KeyboardEvent.parse_raw(
            json.dumps(
                {
                    "timestamp": "2023-05-01T10:26:52.625731",
                    "screenshot": None,
                    "device": "keyboard",
                    "action": "press",
                    "key": json_key_field,
                }
            )
        )

        assert subject == events.KeyboardEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"),
            action="press",
            key=key,
        )


class TestEvents:
    @staticmethod
    def test_length_represents_number_of_events_saved():
        event1 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        event2 = events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))
        event3 = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))
        event4 = events.KeyboardEvent(action="press", key="a")
        event5 = events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1))

        all_events = events.Events()
        all_events.append(event1)
        all_events.append(event2)
        all_events.append(event3)
        all_events.append(event4)
        all_events.append(event5)

        assert len(all_events) == 5

    @staticmethod
    def test_getting_element():
        event1 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        event2 = events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))
        event3 = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))
        event4 = events.KeyboardEvent(action="press", key="a")
        event5 = events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1))

        all_events = events.Events()
        all_events.append(event1)
        all_events.append(event2)
        all_events.append(event3)
        all_events.append(event4)
        all_events.append(event5)

        assert all_events[2] == event3

    @staticmethod
    def test_iterating_over_elements():
        event_collection = [
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.KeyboardEvent(action="press", key="a"),
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
        ]

        subject = events.Events()
        for event in event_collection:
            subject.append(event)

        for i, event in enumerate(subject):
            assert event == event_collection[i]

    @staticmethod
    @pytest.mark.parametrize("iterable_type", [list, tuple, iter])
    def test_from_iterable(iterable_type):
        event_collection = [
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.KeyboardEvent(action="press", key="a"),
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
        ]

        subject = events.Events.from_iterable(iterable_type(event_collection))

        for i, event in enumerate(subject):
            assert event == event_collection[i]

    @staticmethod
    def test_events_serializes():
        event1 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        event2 = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))
        event3 = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))
        event4 = events.KeyboardEvent(action="press", key=SpecialKey.ALT)
        event5 = events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1))

        subject = events.Events()
        subject.append(event1)
        subject.append(event2)
        subject.append(event3)
        subject.append(event4)
        subject.append(event5)

        actual = subject.json()

        expected = [
            {"screenshot": ".", "device": "state", "location": {"x": 1, "y": 1}},
            {
                "screenshot": None,
                "device": "mouse",
                "action": "release",
                "button": "left",
                "location": {"x": 1, "y": 1},
            },
            {
                "screenshot": None,
                "device": "mouse",
                "action": "scroll",
                "location": {"x": 1, "y": 1},
                "scroll": {"dx": -2, "dy": 5},
            },
            {
                "screenshot": None,
                "device": "keyboard",
                "action": "press",
                "key": {"donkey_see_donkey_do": None, "type": "key", "key": SpecialKey.ALT.value},
            },
            {
                "screenshot": None,
                "device": "mouse",
                "action": "click",
                "button": "left",
                "location": {"x": 1, "y": 1},
                "n_clicks": 1,
            },
        ]

        assert_serialized_objects_equal(actual, expected)

    @staticmethod
    def test_deserialize_events():
        subject = events.Events.parse_raw(
            json.dumps(
                [
                    {
                        "timestamp": "2023-05-01T10:26:52.625731",
                        "screenshot": ".",
                        "device": "state",
                        "location": {"x": 1, "y": 1},
                    },
                    {
                        "timestamp": "2023-05-01T10:26:52.625731",
                        "screenshot": None,
                        "device": "mouse",
                        "action": "release",
                        "button": "left",
                        "location": {"x": 1, "y": 1},
                    },
                    {
                        "timestamp": "2023-05-01T10:26:52.625731",
                        "screenshot": None,
                        "device": "mouse",
                        "action": "scroll",
                        "location": {"x": 1, "y": 1},
                        "scroll": {"dx": -2, "dy": 5},
                    },
                    {
                        "timestamp": "2023-05-01T10:26:52.625731",
                        "screenshot": None,
                        "device": "keyboard",
                        "action": "press",
                        "key": {"donkey_see_donkey_do": None, "type": "key", "key": SpecialKey.ALT.value},
                    },
                    {
                        "timestamp": "2023-05-01T10:26:52.625731",
                        "screenshot": None,
                        "device": "mouse",
                        "action": "click",
                        "button": "left",
                        "location": {"x": 1, "y": 1},
                        "n_clicks": 1,
                    },
                ]
            )
        )

        assert len(subject) == 5
        assert subject[0] == events.StateSnapshotEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"), screenshot=Path("."), location=Point(1, 1)
        )
        assert subject[1] == events.MouseButtonEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"),
            action="release",
            button=MouseButton.LEFT,
            location=Point(1, 1),
        )
        assert subject[2] == events.ScrollEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"), location=Point(1, 1), scroll=(-2, 5)
        )
        assert subject[3] == events.KeyboardEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"), action="press", key=SpecialKey.ALT
        )
        assert subject[4] == events.ClickEvent(
            timestamp=datetime.fromisoformat("2023-05-01T10:26:52.625731"),
            button=MouseButton.LEFT,
            location=Point(1, 1),
        )
