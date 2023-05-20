from datetime import datetime
from pathlib import Path

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
