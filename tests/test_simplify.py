from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pin_the_tail.interaction import MouseButton, SpecialKey
from pin_the_tail.location import Point

from donkey_see_donkey_do import events, simplify


class TestDropConsecutiveStateSnapshots:
    @staticmethod
    def test_no_snapshots_returns_unaltered_events():
        event0 = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))
        event1 = events.KeyboardEvent(action="press", key=SpecialKey.ALT)

        actual_events = simplify.drop_consecutive_state_snapshots(event0, event1)

        assert actual_events == [event0, event1]

    @staticmethod
    @pytest.mark.parametrize(
        "event0, event1",
        [
            (
                events.KeyboardEvent(action="press", key=SpecialKey.ALT),
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
            ),
            (
                events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1)),
                events.KeyboardEvent(action="press", key=SpecialKey.ALT),
            ),
        ],
    )
    def test_one_snapshot_is_kept_if_only_one_snapshot(event0, event1):
        actual_events = simplify.drop_consecutive_state_snapshots(event0, event1)

        assert actual_events == [event0, event1]

    @staticmethod
    def test_consecutive_snapshots_keeps_only_second():
        event0 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        event1 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 2))

        actual_events = simplify.drop_consecutive_state_snapshots(event0, event1)

        assert actual_events == [event1]


class TestMousePressReleaseToClick:
    @staticmethod
    def test_no_mouse_button_presses_returns_unaltered_events():
        event0 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        event1 = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))

        actual_events = simplify.merge_consecutive_mouse_press_then_release_to_click(event0, event1)

        assert actual_events == [event0, event1]

    @staticmethod
    def test_mouse_button_press_release_converted_to_click():
        press_event = events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))
        release_event = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))

        actual_events = simplify.merge_consecutive_mouse_press_then_release_to_click(press_event, release_event)

        assert actual_events == [
            events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1), timestamp=press_event.timestamp)
        ]

    @staticmethod
    def test_mouse_button_press_press_not_converted_to_click():
        press_event1 = events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))
        press_event2 = events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))

        actual_events = simplify.merge_consecutive_mouse_press_then_release_to_click(press_event1, press_event2)

        assert actual_events == [press_event1, press_event2]

    @staticmethod
    def test_mouse_button_release_release_not_converted_to_click():
        press_event1 = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))
        press_event2 = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 1))

        actual_events = simplify.merge_consecutive_mouse_press_then_release_to_click(press_event1, press_event2)

        assert actual_events == [press_event1, press_event2]

    @staticmethod
    def test_mouse_button_press_release_of_different_buttons_not_converted_to_click():
        press_event = events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))
        release_event = events.MouseButtonEvent(action="release", button=MouseButton.RIGHT, location=Point(1, 1))

        actual_events = simplify.merge_consecutive_mouse_press_then_release_to_click(press_event, release_event)

        assert actual_events == [press_event, release_event]

    @staticmethod
    def test_mouse_button_press_release_not_converted_to_click_if_separated_by_too_much_time():
        press_event = events.MouseButtonEvent(
            action="press", button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 4, 28, 7, 0, 0)
        )
        release_event = events.MouseButtonEvent(
            action="release", button=MouseButton.LEFT, location=Point(1, 1), timestamp=datetime(2023, 4, 28, 8, 0, 0)
        )

        actual_events = simplify.merge_consecutive_mouse_press_then_release_to_click(
            press_event, release_event, max_seconds=1
        )

        assert actual_events == [press_event, release_event]

    @staticmethod
    def test_mouse_button_press_release_not_converted_to_click_if_mouse_moved_too_much():
        press_event = events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))
        release_event = events.MouseButtonEvent(action="release", button=MouseButton.LEFT, location=Point(1, 10))

        actual_events = simplify.merge_consecutive_mouse_press_then_release_to_click(
            press_event, release_event, max_pixels=1
        )

        assert actual_events == [press_event, release_event]

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

        simplify.merge_consecutive_mouse_press_then_release_to_click(press_event, release_event)

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
        event0 = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))
        event1 = events.MouseButtonEvent(action="press", button=MouseButton.LEFT, location=Point(1, 1))

        actual_events = simplify.merge_consecutive_mouse_clicks_to_multi_click(event0, event1)

        assert actual_events == [event0, event1]

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
        actual_events = simplify.merge_consecutive_mouse_clicks_to_multi_click(first_click, second_click)

        assert actual_events == [
            events.ClickEvent(
                button=MouseButton.LEFT,
                location=Point(1, 1),
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 0),
                n_clicks=2,
                last_timestamp=datetime(2023, 5, 20, 7, 11, 48, 1),
            )
        ]

    @staticmethod
    def test_n_clicks_is_sum_of_original_clicks():
        first_click = events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1), n_clicks=2)
        second_click = events.ClickEvent(button=MouseButton.LEFT, location=Point(1, 1), n_clicks=7)

        actual_events = simplify.merge_consecutive_mouse_clicks_to_multi_click(first_click, second_click)

        expected_click = first_click.copy()
        expected_click.n_clicks = 9
        expected_click.last_timestamp = second_click.timestamp

        assert actual_events == [expected_click]

    @staticmethod
    def test_clicks_merged_when_second_starts_too_long_after_first_started_but_soon_enough_after_first_ended():
        first_click = events.ClickEvent(
            timestamp=datetime(2023, 5, 20, 7, 1, 0),
            button=MouseButton.LEFT,
            location=Point(1, 1),
            n_clicks=3,
            last_timestamp=datetime(2023, 5, 20, 7, 1, 3),
        )
        second_click = events.ClickEvent(
            timestamp=datetime(2023, 5, 20, 7, 1, 5), button=MouseButton.LEFT, location=Point(1, 1)
        )

        actual_events = simplify.merge_consecutive_mouse_clicks_to_multi_click(
            first_click, second_click, max_seconds=2.1
        )

        expected_click = first_click.copy()
        expected_click.n_clicks = 4
        expected_click.last_timestamp = second_click.timestamp

        assert actual_events == [expected_click]

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
        actual_events = simplify.merge_consecutive_mouse_clicks_to_multi_click(first_click, second_click)

        assert actual_events == [first_click, second_click]

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
        actual_events = simplify.merge_consecutive_mouse_clicks_to_multi_click(first_click, second_click, max_seconds=1)

        assert actual_events == [first_click, second_click]

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
        actual_events = simplify.merge_consecutive_mouse_clicks_to_multi_click(first_click, second_click, max_pixels=1)

        assert actual_events == [first_click, second_click]

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

        simplify.merge_consecutive_mouse_clicks_to_multi_click(click_1, click_2)

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

        simplify.merge_consecutive_mouse_clicks_to_multi_click(click_1, click_2)

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
        event0 = events.StateSnapshotEvent(screenshot=Path("."), location=Point(1, 1))
        event1 = events.ScrollEvent(location=Point(1, 1), scroll=(-2, 5))

        actual_events = simplify.merge_consecutive_key_press_then_release_to_write(event0, event1)

        assert actual_events == [event0, event1]

    @staticmethod
    def test_key_press_release_converted_to_click():
        press_event = events.KeyboardEvent(action="press", key="a")
        release_event = events.KeyboardEvent(action="release", key="a")

        actual_events = simplify.merge_consecutive_key_press_then_release_to_write(press_event, release_event)

        expected_write_event = events.WriteEvent(timestamp=press_event.timestamp, keys="a")
        assert actual_events == [expected_write_event]

    @staticmethod
    def test_key_press_press_not_converted_to_click():
        event_press1 = events.KeyboardEvent(action="press", key="a")
        event_press2 = events.KeyboardEvent(action="press", key="a")

        actual_events = simplify.merge_consecutive_key_press_then_release_to_write(event_press1, event_press2)

        assert actual_events == [event_press1, event_press2]

    @staticmethod
    def test_mouse_button_release_release_not_converted_to_click():
        event_release1 = events.KeyboardEvent(action="release", key="a")
        event_release2 = events.KeyboardEvent(action="release", key="a")

        actual_events = simplify.merge_consecutive_key_press_then_release_to_write(event_release1, event_release2)

        assert actual_events == [event_release1, event_release2]

    @staticmethod
    def test_mouse_button_press_release_of_different_buttons_not_converted_to_click():
        event_press = events.KeyboardEvent(action="press", key="a")
        event_release = events.KeyboardEvent(action="release", key="b")

        actual_events = simplify.merge_consecutive_key_press_then_release_to_write(event_press, event_release)

        assert actual_events == [event_press, event_release]

    @staticmethod
    def test_mouse_button_press_release_not_converted_to_click_if_separated_by_too_much_time():
        press_event = events.KeyboardEvent(action="press", key="a", timestamp=datetime(2023, 4, 28, 7, 0, 0))
        release_event = events.KeyboardEvent(action="release", key="a", timestamp=datetime(2023, 4, 28, 7, 0, 2))

        actual_events = simplify.merge_consecutive_key_press_then_release_to_write(
            press_event, release_event, max_seconds=1
        )

        assert actual_events == [press_event, release_event]

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

        simplify.merge_consecutive_key_press_then_release_to_write(press_event, release_event)

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


class TestMergeConsecutiveWriteEvents:
    @staticmethod
    def test_no_write_returns_unaltered_events():
        event0 = events.KeyboardEvent(action="press", key="a")
        event1 = events.KeyboardEvent(action="release", key="a")

        actual_events = simplify.merge_consecutive_write_events(event0, event1)

        assert actual_events == [event0, event1]

    @staticmethod
    def test_two_sequential_writes_converted_to_single_write():
        first_write = events.WriteEvent(timestamp=datetime(2023, 5, 20, 7, 11, 48, 0), keys=["a", SpecialKey.ALT])
        second_write = events.WriteEvent(timestamp=datetime(2023, 5, 20, 7, 11, 48, 1), keys=["b"])

        actual_events = simplify.merge_consecutive_write_events(first_write, second_write)

        assert len(actual_events) == 1
        assert actual_events == [
            events.WriteEvent(
                timestamp=datetime(2023, 5, 20, 7, 11, 48, 0),
                last_timestamp=datetime(2023, 5, 20, 7, 11, 48, 1),
                keys=["a", SpecialKey.ALT, "b"],
            )
        ]

    @staticmethod
    def test_writes_merged_when_second_starts_too_long_after_first_started_but_soon_enough_after_first_ended():
        first_write = events.WriteEvent(
            timestamp=datetime(2023, 5, 20, 7, 1, 0),
            keys=["a", "b"],
            last_timestamp=datetime(2023, 5, 20, 7, 1, 3),
        )
        second_write = events.WriteEvent(timestamp=datetime(2023, 5, 20, 7, 1, 5), keys="c")

        actual_events = simplify.merge_consecutive_write_events(first_write, second_write, max_seconds=2.1)

        assert actual_events == [
            events.WriteEvent(
                timestamp=first_write.timestamp,
                last_timestamp=second_write.timestamp,
                keys=["a", "b", "c"],
            )
        ]

    @staticmethod
    def test_two_writes_are_not_merged_if_separated_by_too_much_time():
        first_write = events.WriteEvent(
            timestamp=datetime(2023, 5, 20, 7, 11, 48),
            keys=["a", "b"],
        )
        second_write = events.WriteEvent(timestamp=datetime(2023, 5, 20, 7, 11, 50), keys="c")

        actual_events = simplify.merge_consecutive_write_events(first_write, second_write, max_seconds=1)

        assert actual_events == [first_write, second_write]

    @staticmethod
    def test_original_events_are_unmodified():
        event1 = events.WriteEvent(
            timestamp=datetime(2023, 5, 20, 7, 11, 48),
            keys=["a", "b"],
        )
        event2 = events.WriteEvent(timestamp=datetime(2023, 5, 20, 7, 11, 49), keys="c")

        simplify.merge_consecutive_write_events(event1, event2)

        assert event1 == events.WriteEvent(
            timestamp=datetime(2023, 5, 20, 7, 11, 48),
            keys=["a", "b"],
        )
        assert event2 == events.WriteEvent(timestamp=datetime(2023, 5, 20, 7, 11, 49), keys="c")


class TestMergeConsecutiveScrollEvents:
    @staticmethod
    @pytest.mark.parametrize(
        "event1, event2",
        [
            (events.ScrollEvent(location=(1, 1), scroll=(1, 0)), events.WriteEvent()),
            (events.WriteEvent(), events.ScrollEvent(location=(1, 1), scroll=(1, 0))),
            (events.WriteEvent(), events.WriteEvent()),
        ],
    )
    def test_events_returned_if_at_least_one_isnt_a_scroll_event(event1, event2):
        actual = simplify.merge_consecutive_scroll_events(event1, event2)

        assert actual == [event1, event2]

    @staticmethod
    def test_events_unmerged_if_separated_by_too_much_time():
        event1 = events.ScrollEvent(timestamp=datetime(2023, 5, 20, 7, 11, 48), location=(1, 1), scroll=(1, 0))
        event2 = events.ScrollEvent(timestamp=datetime(2023, 5, 20, 7, 12, 48), location=(1, 1), scroll=(3, 0))

        actual = simplify.merge_consecutive_scroll_events(event1, event2, max_seconds=1)

        assert actual == [event1, event2]

    @staticmethod
    def test_events_unmerged_if_last_timestamp_of_first_is_much_earlier_than_timestamp_of_second():
        event1 = events.ScrollEvent(
            timestamp=datetime(2023, 5, 20, 7, 11, 48),
            location=(1, 1),
            scroll=(1, 0),
            last_timestamp=datetime(2023, 5, 20, 7, 11, 50),
        )
        event2 = events.ScrollEvent(timestamp=datetime(2023, 5, 20, 7, 12, 48), location=(1, 1), scroll=(3, 0))

        actual = simplify.merge_consecutive_scroll_events(event1, event2, max_seconds=2)

        assert actual == [event1, event2]

    @staticmethod
    def test_events_merge_when_first_starts_much_earlier_but_ends_close_enough_to_start_of_second():
        event1 = events.ScrollEvent(
            timestamp=datetime(2023, 5, 20, 7, 11, 48),
            location=(1, 1),
            scroll=(1, 0),
            last_timestamp=datetime(2023, 5, 20, 7, 12, 47),
        )
        event2 = events.ScrollEvent(timestamp=datetime(2023, 5, 20, 7, 12, 48), location=(1, 1), scroll=(3, 0))
        event_merged = event1.copy()
        event_merged.update_with(event2)

        actual = simplify.merge_consecutive_scroll_events(event1, event2, max_seconds=2)

        assert actual == [event_merged]

    @staticmethod
    def test_events_unmerged_if_separated_by_too_many_pixels():
        event1 = events.ScrollEvent(location=(1, 1), scroll=(1, 0))
        event2 = events.ScrollEvent(location=(1, 20), scroll=(3, 0))

        actual = simplify.merge_consecutive_scroll_events(event1, event2, max_pixels=1)

        assert actual == [event1, event2]

    @staticmethod
    @pytest.mark.parametrize("dx_1, dx_2", [(0, 0), (0, 1), (1, 0), (1, 1), (0, -1), (-1, 0), (-1, -1)])
    @pytest.mark.parametrize("dy_1, dy_2", [(0, 0), (0, 1), (1, 0), (1, 1), (0, -1), (-1, 0), (-1, -1)])
    def test_events_merge_if_scroll_directions_compatible(dx_1, dx_2, dy_1, dy_2):
        event1 = events.ScrollEvent(location=(1, 1), scroll=(dx_1, dy_1))
        event2 = events.ScrollEvent(location=(1, 1), scroll=(dx_2, dy_2))
        event_merged = event1.copy()
        event_merged.update_with(event2)

        actual = simplify.merge_consecutive_scroll_events(event1, event2)

        assert actual == [event_merged]

    @staticmethod
    @pytest.mark.parametrize("dx_1, dx_2", [(0, 0), (-1, 1), (1, -1)])
    @pytest.mark.parametrize("dy_1, dy_2", [(0, 0), (-1, 1), (1, -1)])
    def test_events_merged_if_merge_opposite_directions_is_true(dx_1, dy_1, dx_2, dy_2):
        event1 = events.ScrollEvent(location=(1, 1), scroll=(dx_1, dy_1))
        event2 = events.ScrollEvent(location=(1, 1), scroll=(dx_2, dy_2))
        event_merged = event1.copy()
        event_merged.update_with(event2)

        actual = simplify.merge_consecutive_scroll_events(event1, event2, merge_opposite_directions=True)

        assert actual == [event_merged]

    @staticmethod
    @pytest.mark.parametrize("dx_1, dx_2", [(-1, 1), (1, -1)])
    @pytest.mark.parametrize("dy_1, dy_2", [(-1, 1), (1, -1)])
    def test_events_not_merged_if_scrolls_are_in_opposite_directions(dx_1, dy_1, dx_2, dy_2):
        event1 = events.ScrollEvent(location=(1, 1), scroll=(dx_1, dy_1))
        event2 = events.ScrollEvent(location=(1, 1), scroll=(dx_2, dy_2))

        actual = simplify.merge_consecutive_scroll_events(event1, event2)

        assert actual == [event1, event2]

    @staticmethod
    def test_original_events_are_unmodified():
        event1 = events.ScrollEvent(timestamp=datetime(2023, 5, 20, 7, 11, 48), location=(1, 1), scroll=(1, 0))
        event2 = events.ScrollEvent(timestamp=datetime(2023, 5, 20, 7, 11, 49), location=(1, 1), scroll=(3, 0))

        simplify.merge_consecutive_scroll_events(event1, event2, max_seconds=10)

        assert event1 == events.ScrollEvent(timestamp=datetime(2023, 5, 20, 7, 11, 48), location=(1, 1), scroll=(1, 0))
        assert event2 == events.ScrollEvent(timestamp=datetime(2023, 5, 20, 7, 11, 49), location=(1, 1), scroll=(3, 0))


class TestMergeConsecutiveEvents:
    @staticmethod
    def test_empty_events_returns_empty_events():
        subject = events.Events()
        mock_merger = MagicMock()

        actual = simplify.merge_consecutive_events(subject, [mock_merger])

        assert actual is subject
        mock_merger.assert_not_called()

    @staticmethod
    def test_one_event_returns_that_event():
        subject = events.Events.from_iterable([MagicMock()])
        mock_merger = MagicMock()

        actual = simplify.merge_consecutive_events(subject, [mock_merger])

        assert actual is subject
        mock_merger.assert_not_called()

    @staticmethod
    def test_no_mergers_returns_events_unmerged():
        event0 = MagicMock()
        event1 = MagicMock()
        event2 = MagicMock()
        event3 = MagicMock()
        subject = events.Events.from_iterable([event0, event1, event2, event3])

        actual = simplify.merge_consecutive_events(subject, [])

        assert actual == subject

    @staticmethod
    def test_two_events_merged_into_one():
        event0 = events.WriteEvent(keys="a")
        event1 = events.WriteEvent(keys="b")
        event_merged01 = events.WriteEvent(keys="ab")
        subject = events.Events.from_iterable([event0, event1])

        def merger(event_a, event_b):
            if event_a == event0 and event_b == event1:
                return [event_merged01]
            return [event_a, event_b]

        actual = simplify.merge_consecutive_events(subject, [merger])

        assert actual == events.Events.from_iterable([event_merged01])

    @staticmethod
    def test_two_unmergeable_events_remain_unmerged():
        event0 = events.WriteEvent(keys="a")
        event1 = events.WriteEvent(keys="b")
        subject = events.Events.from_iterable([event0, event1])

        def merger(event_a, event_b):
            return [event_a, event_b]

        actual = simplify.merge_consecutive_events(subject, [merger])

        assert actual == events.Events.from_iterable([event0, event1])

    @staticmethod
    def test_merged_event_can_be_merged_with_subsequent_event():
        event0 = events.WriteEvent(keys="a")
        event1 = events.WriteEvent(keys="b")
        event2 = events.WriteEvent(keys="c")
        event_merged01 = events.WriteEvent(keys="ab")
        event_merged012 = events.WriteEvent(keys="abc")
        subject = events.Events.from_iterable([event0, event1, event2])

        def merger(event_a, event_b):
            if event_a == event0 and event_b == event1:
                return [event_merged01]
            if event_a == event_merged01 and event_b == event2:
                return [event_merged012]
            return [event_a, event_b]

        actual = simplify.merge_consecutive_events(subject, [merger])

        assert actual == events.Events.from_iterable([event_merged012])

    @staticmethod
    def test_events_not_merged_if_separated_by_unmergeable_event():
        event0 = events.WriteEvent(keys="a")
        event1 = events.WriteEvent(keys="b")
        event2 = events.WriteEvent(keys="c")
        event_merged02 = events.WriteEvent(keys="ac")
        subject = events.Events.from_iterable([event0, event1, event2])

        def merger(event_a, event_b):
            if event_a == event0 and event_b == event2:
                return [event_merged02]
            return [event_a, event_b]

        actual = simplify.merge_consecutive_events(subject, [merger])

        assert actual == events.Events.from_iterable([event0, event1, event2])

    @staticmethod
    def test_second_merger_called_if_first_merger_doesnt_merge():
        event0 = events.WriteEvent(keys="a")
        event1 = events.WriteEvent(keys="b")
        event_merged01 = events.WriteEvent(keys="ab")
        subject = events.Events.from_iterable([event0, event1])

        def merger1(event_a, event_b):
            return [event_a, event_b]

        def merger2(event_a, event_b):
            if event_a == event0 and event_b == event1:
                return [event_merged01]
            return [event_a, event_b]

        actual = simplify.merge_consecutive_events(subject, [merger1, merger2])

        assert actual == events.Events.from_iterable([event_merged01])
