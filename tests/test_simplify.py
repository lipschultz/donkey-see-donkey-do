from datetime import datetime
from pathlib import Path

import pytest
from pin_the_tail.interaction import MouseButton, SpecialKey
from pin_the_tail.location import Point

from donkey_see_donkey_do import events, simplify


class TestDropConsecutiveStateSnapshots:
    @staticmethod
    def test_no_snapshots_returns_unaltered_events():
        subject = events.Events.from_iterable(
            (
                events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1)),
                events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
                events.KeyboardEvent(action="press", key=SpecialKey.ALT),
            )
        )

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == subject

    @staticmethod
    def test_one_snapshot_in_middle_of_events_is_kept():
        subject = events.Events.from_iterable(
            (
                events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1)),
                events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
                events.KeyboardEvent(action="press", key=SpecialKey.ALT),
            )
        )

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == subject

    @staticmethod
    def test_one_snapshot_at_start_of_events_is_kept():
        subject = events.Events.from_iterable(
            (
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
                events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1)),
                events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
                events.KeyboardEvent(action="press", key=SpecialKey.ALT),
            )
        )

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == subject

    @staticmethod
    def test_one_snapshot_at_end_of_events_is_kept():
        subject = events.Events.from_iterable(
            (
                events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1)),
                events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
                events.KeyboardEvent(action="press", key=SpecialKey.ALT),
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            )
        )

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == subject

    @staticmethod
    def test_no_events_results_in_empty_events_returned():
        subject = events.Events()

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == subject

    @staticmethod
    def test_all_snapshots_are_kept_when_multiple_one_snapshot_runs_in_events():
        subject = events.Events.from_iterable(
            (
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
                events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1)),
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
                events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
                events.KeyboardEvent(action="press", key=SpecialKey.ALT),
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            )
        )

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == subject

    @staticmethod
    def test_multiple_snapshots_in_middle_of_events_keeps_only_last():
        click_event = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))
        scroll_event = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))
        keyboard_event = events.KeyboardEvent(action="press", key=SpecialKey.ALT)
        snapshot_1 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        snapshot_2 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 2))
        snapshot_3 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 3))
        subject = events.Events.from_iterable(
            (click_event, scroll_event, snapshot_1, snapshot_2, snapshot_3, keyboard_event)
        )

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == events.Events.from_iterable((click_event, scroll_event, snapshot_3, keyboard_event))

    @staticmethod
    def test_multiple_snapshots_at_start_of_events_keeps_only_last():
        click_event = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))
        scroll_event = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))
        keyboard_event = events.KeyboardEvent(action="press", key=SpecialKey.ALT)
        snapshot_1 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        snapshot_2 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 2))
        snapshot_3 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 3))
        subject = events.Events.from_iterable(
            (snapshot_1, snapshot_2, snapshot_3, click_event, scroll_event, keyboard_event)
        )

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == events.Events.from_iterable((snapshot_3, click_event, scroll_event, keyboard_event))

    @staticmethod
    def test_multiple_snapshots_at_end_of_events_keeps_only_last():
        click_event = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))
        scroll_event = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))
        keyboard_event = events.KeyboardEvent(action="press", key=SpecialKey.ALT)
        snapshot_1 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        snapshot_2 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 2))
        snapshot_3 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 3))
        subject = events.Events.from_iterable(
            (click_event, scroll_event, keyboard_event, snapshot_1, snapshot_2, snapshot_3)
        )

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == events.Events.from_iterable((click_event, scroll_event, keyboard_event, snapshot_3))

    @staticmethod
    def test_only_last_snapshot_kept_when_events_is_just_snapshots():
        snapshot_1 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        snapshot_2 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 2))
        snapshot_3 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 3))
        subject = events.Events.from_iterable((snapshot_1, snapshot_2, snapshot_3))

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == events.Events.from_iterable([snapshot_3])

    @staticmethod
    def test_events_returned_unaltered_when_events_is_just_one_snapshot():
        subject = events.Events.from_iterable([events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))])

        actual_events = simplify.drop_consecutive_state_snapshots(subject)

        assert actual_events == subject


class TestMousePressReleaseToClick:
    @staticmethod
    def test_no_mouse_button_presses_returns_unaltered_events():
        subject = events.Events.from_iterable(
            (
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
                events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
                events.KeyboardEvent(action="press", key=SpecialKey.ALT),
            )
        )

        actual_events = simplify.convert_mouse_press_then_release_to_click(subject)

        assert actual_events == subject

    @staticmethod
    def test_mouse_button_press_release_converted_to_click():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1)),
            events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1)),
            events.KeyboardEvent(action="press", key=SpecialKey.ALT),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_mouse_press_then_release_to_click(subject)

        assert actual_events == events.Events.from_iterable(
            event_collection[:2]
            + (
                events.ClickEvent(
                    button=MouseButton.LEFT, location=Point(1, 1), timestamp=event_collection[2].timestamp
                ),
            )
            + event_collection[4:]
        )

    @staticmethod
    def test_mouse_button_press_press_not_converted_to_click():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1)),
            events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1)),
            events.KeyboardEvent(action="press", key=SpecialKey.ALT),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_mouse_press_then_release_to_click(subject)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_mouse_button_release_release_not_converted_to_click():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1)),
            events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1)),
            events.KeyboardEvent(action="press", key=SpecialKey.ALT),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_mouse_press_then_release_to_click(subject)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_mouse_button_press_release_of_different_buttons_not_converted_to_click():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1)),
            events.MouseButtonEvent(action="release", button=MouseButton.RIGHT, location=Point(1, 1)),
            events.KeyboardEvent(action="press", key=SpecialKey.ALT),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_mouse_press_then_release_to_click(subject)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_mouse_button_press_release_not_converted_to_click_if_separated_by_too_much_time():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.MouseButtonEvent(
                action="press",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime.fromisoformat("2023-05-01T10:00:00.000000"),
            ),
            events.MouseButtonEvent(
                action="release",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime.fromisoformat("2023-05-01T11:00:00.000000"),
            ),
            events.KeyboardEvent(action="press", key=SpecialKey.ALT),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_mouse_press_then_release_to_click(subject, max_seconds=1)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_mouse_button_press_release_not_converted_to_click_if_separated_by_another_event():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1)),
            events.KeyboardEvent(action="press", key=SpecialKey.ALT),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_mouse_press_then_release_to_click(subject)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_mouse_button_press_release_not_converted_to_click_if_mouse_moved_too_much():
        event_collection = (
            events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1)),
            events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 10)),
            events.KeyboardEvent(action="press", key=SpecialKey.ALT),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_mouse_press_then_release_to_click(subject, max_pixels=5)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_original_events_are_unmodified():
        press_event = events.MouseButtonEvent(
            action="press",
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 48, 374094),
        )
        release_event = events.MouseButtonEvent(
            action="release",
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 49, 0),
        )

        subject = events.Events.from_iterable([press_event, release_event])

        simplify.convert_mouse_press_then_release_to_click(subject)

        assert press_event == events.MouseButtonEvent(
            action="press",
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 48, 374094),
        )
        assert release_event == events.MouseButtonEvent(
            action="release",
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 49, 0),
        )


class TestConvertMouseClicksToMultiClicks:
    @staticmethod
    def test_no_clicks_returns_unaltered_events():
        subject = events.Events.from_iterable(
            (
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
                events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
                events.KeyboardEvent(action="press", key=SpecialKey.ALT),
                events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1)),
            )
        )

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject)

        assert actual_events == subject

    @staticmethod
    @pytest.mark.parametrize(
        "first_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 0),
            ),
            events.ClickEvent(
                button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 48, 0)
            ),
        ],
    )
    @pytest.mark.parametrize(
        "second_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 1),
            ),
            events.ClickEvent(
                button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 48, 1)
            ),
        ],
    )
    def test_two_sequential_clicks_converted_to_single_multi_click(first_click, second_click):
        subject = events.Events.from_iterable((first_click, second_click))

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject)

        assert len(actual_events) == 1
        assert actual_events[0] == events.ClickEvent(
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 48, 0),
            n_clicks=2,
            last_timestamp=datetime(2023, 5, 20, 7, 11, 48, 1),
        )

    @staticmethod
    def test_n_clicks_is_sum_of_original_clicks():
        subject = events.Events.from_iterable(
            (
                events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1), n_clicks=2),
                events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1), n_clicks=7),
            )
        )

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject)

        assert len(actual_events) == 1
        assert actual_events[0].n_clicks == 9

    @staticmethod
    def test_many_click_events_converted_to_one_multi_click_event():
        subject = events.Events.from_iterable(
            (
                events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1), n_clicks=2),
                events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1), n_clicks=7),
                events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
                events.MouseButtonEvent(
                    action="click",
                    button=MouseButton.LEFT,
                    location=Point(1, 1),
                ),
            )
        )

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject)

        assert len(actual_events) == 1
        assert actual_events[0].n_clicks == 11
        assert actual_events[0].timestamp == subject[0].timestamp

    @staticmethod
    def test_clicks_merged_when_first_and_last_are_separated_by_more_than_max_seconds():
        subject = events.Events.from_iterable(
            (
                events.ClickEvent(
                    timestamp=datetime(2023, 5, 20, 7, 1, 0, 0), button=MouseButton.LEFT, location=Point(1, 1)
                ),
                events.ClickEvent(
                    timestamp=datetime(2023, 5, 20, 7, 1, 2, 0), button=MouseButton.LEFT, location=Point(1, 1)
                ),
                events.ClickEvent(
                    timestamp=datetime(2023, 5, 20, 7, 1, 4, 0), button=MouseButton.LEFT, location=Point(1, 1)
                ),
                events.ClickEvent(
                    timestamp=datetime(2023, 5, 20, 7, 1, 6, 0), button=MouseButton.LEFT, location=Point(1, 1)
                ),
            )
        )

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject, max_seconds=3)

        assert len(actual_events) == 1
        assert actual_events[0].n_clicks == 4
        assert actual_events[0].timestamp == subject[0].timestamp

    @staticmethod
    def test_clicks_merged_when_second_starts_too_long_after_first_started_but_soon_enough_after_first_ended():
        subject = events.Events.from_iterable(
            (
                events.ClickEvent(
                    timestamp=datetime(2023, 5, 20, 7, 1, 0, 0),
                    button=MouseButton.LEFT,
                    location=Point(1, 1),
                    n_clicks=3,
                    last_timestamp=datetime(2023, 5, 20, 7, 1, 3, 0),
                ),
                events.ClickEvent(
                    timestamp=datetime(2023, 5, 20, 7, 1, 5, 0), button=MouseButton.LEFT, location=Point(1, 1)
                ),
            )
        )

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject, max_seconds=2.1)

        assert len(actual_events) == 1
        assert actual_events[0].n_clicks == 4
        assert actual_events[0].timestamp == subject[0].timestamp

    @staticmethod
    @pytest.mark.parametrize(
        "first_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 0),
            ),
            events.ClickEvent(
                button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 48, 0)
            ),
        ],
    )
    @pytest.mark.parametrize(
        "second_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.RIGHT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 1),
            ),
            events.ClickEvent(
                button=MouseButton.RIGHT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 48, 1)
            ),
        ],
    )
    def test_clicks_of_different_buttons_not_merged(first_click, second_click):
        subject = events.Events.from_iterable((first_click, second_click))

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject)

        assert len(actual_events) == 2
        assert actual_events == subject

    @staticmethod
    @pytest.mark.parametrize(
        "first_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 0),
            ),
            events.ClickEvent(
                button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 48, 0)
            ),
        ],
    )
    @pytest.mark.parametrize(
        "second_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 2),
            ),
            events.ClickEvent(
                button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 48, 2)
            ),
        ],
    )
    def test_two_clicks_separated_by_non_mergeable_event_not_converted_to_multi_click(first_click, second_click):
        subject = events.Events.from_iterable(
            (
                first_click,
                events.ClickEvent(
                    button=MouseButton.RIGHT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 48, 1)
                ),
                second_click,
            )
        )

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject)

        assert len(actual_events) == 3
        assert actual_events == subject

    @staticmethod
    @pytest.mark.parametrize(
        "first_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 0),
            ),
            events.ClickEvent(
                button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 48, 0)
            ),
        ],
    )
    @pytest.mark.parametrize(
        "second_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 50, 0),
            ),
            events.ClickEvent(
                button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 50, 0)
            ),
        ],
    )
    def test_two_clicks_are_not_converted_to_multi_click_if_separated_by_too_much_time(first_click, second_click):
        subject = events.Events.from_iterable((first_click, second_click))

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject, max_seconds=1)

        assert len(actual_events) == 2
        assert actual_events == subject

    @staticmethod
    @pytest.mark.parametrize(
        "first_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 0),
            ),
            events.ClickEvent(
                button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 5, 20, 7, 11, 48, 0)
            ),
        ],
    )
    @pytest.mark.parametrize(
        "second_click",
        [
            events.MouseButtonEvent(
                action="click",
                button=MouseButton.LEFT,
                location=Point(1, 100),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 1),
            ),
            events.ClickEvent(
                button=MouseButton.LEFT, location=Point(1, 100), timestamp=datetime(2023, 5, 20, 7, 11, 48, 1)
            ),
        ],
    )
    def test_two_clicks_are_not_converted_to_multi_click_if_mouse_moved_too_much(first_click, second_click):
        subject = events.Events.from_iterable((first_click, second_click))

        actual_events = simplify.convert_mouse_clicks_to_multi_click(subject, max_pixels=1)

        assert len(actual_events) == 2
        assert actual_events == subject

    @staticmethod
    def test_original_events_are_unmodified_when_events_are_mouse_button():
        click_1 = events.MouseButtonEvent(
            action="click",
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 48, 374094),
        )
        click_2 = events.MouseButtonEvent(
            action="click",
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 49, 0),
        )

        subject = events.Events.from_iterable([click_1, click_2])

        simplify.convert_mouse_press_then_release_to_click(subject)

        assert click_1 == events.MouseButtonEvent(
            action="click",
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 48, 374094),
        )
        assert click_2 == events.MouseButtonEvent(
            action="click",
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 49, 0),
        )

    @staticmethod
    def test_original_events_are_unmodified_when_events_are_click():
        click_1 = events.ClickEvent(
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 48, 374094),
        )
        click_2 = events.ClickEvent(
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 49, 0),
        )

        subject = events.Events.from_iterable([click_1, click_2])

        simplify.convert_mouse_press_then_release_to_click(subject)

        assert click_1 == events.ClickEvent(
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 48, 374094),
        )
        assert click_2 == events.ClickEvent(
            button=MouseButton.LEFT,
            location=Point(1, 1),
            timestamp=datetime(2023, 5, 20, 7, 11, 49, 0),
        )


class TestConvertKeyPressReleaseToWrite:
    @staticmethod
    def test_no_key_presses_returns_unaltered_events():
        subject = events.Events.from_iterable(
            (
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
                events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
                events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
            )
        )

        actual_events = simplify.convert_key_press_then_release_to_write(subject)

        assert actual_events == subject

    @staticmethod
    def test_key_press_release_converted_to_click():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.KeyboardEvent(action="press", key="a"),
            events.KeyboardEvent(action="release", key="a"),
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_key_press_then_release_to_write(subject)

        expected_write_event = events.WriteEvent(
            timestamp=event_collection[2].timestamp,
        )
        expected_write_event.keys.append("a")
        assert actual_events == events.Events.from_iterable(
            event_collection[:2] + (expected_write_event,) + event_collection[4:]
        )

    @staticmethod
    def test_key_press_press_not_converted_to_click():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.KeyboardEvent(action="press", key="a"),
            events.KeyboardEvent(action="press", key="a"),
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_key_press_then_release_to_write(subject)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_mouse_button_release_release_not_converted_to_click():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.KeyboardEvent(action="release", key="a"),
            events.KeyboardEvent(action="release", key="a"),
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_key_press_then_release_to_write(subject)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_mouse_button_press_release_of_different_buttons_not_converted_to_click():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.KeyboardEvent(action="press", key="a"),
            events.KeyboardEvent(action="release", key="b"),
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_key_press_then_release_to_write(subject)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_mouse_button_press_release_not_converted_to_click_if_separated_by_too_much_time():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.KeyboardEvent(
                action="press", key="a", timestamp=datetime.fromisoformat("2023-05-01T10:00:00.000000")
            ),
            events.KeyboardEvent(
                action="release", key="a", timestamp=datetime.fromisoformat("2023-05-01T11:00:00.000000")
            ),
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_key_press_then_release_to_write(subject, max_seconds=1)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_mouse_button_press_release_not_converted_to_click_if_separated_by_another_event():
        event_collection = (
            events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.KeyboardEvent(action="press", key="a"),
            events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5)),
            events.KeyboardEvent(action="release", key="a"),
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1)),
        )
        subject = events.Events.from_iterable(event_collection)

        actual_events = simplify.convert_key_press_then_release_to_write(subject)

        assert actual_events == events.Events.from_iterable(event_collection)

    @staticmethod
    def test_original_events_are_unmodified():
        press_event = events.KeyboardEvent(
            action="press",
            key="a",
            timestamp=datetime(2023, 5, 20, 7, 11, 48, 374094),
        )
        release_event = events.KeyboardEvent(
            action="release",
            key="a",
            timestamp=datetime(2023, 5, 20, 7, 11, 49, 0),
        )

        subject = events.Events.from_iterable([press_event, release_event])

        simplify.convert_key_press_then_release_to_write(subject)

        assert press_event == events.KeyboardEvent(
            action="press",
            key="a",
            timestamp=datetime(2023, 5, 20, 7, 11, 48, 374094),
        )
        assert release_event == events.KeyboardEvent(
            action="release",
            key="a",
            timestamp=datetime(2023, 5, 20, 7, 11, 49, 0),
        )
