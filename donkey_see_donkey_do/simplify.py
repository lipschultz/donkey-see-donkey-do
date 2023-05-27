import math
from typing import Callable, Iterable, List

from donkey_see_donkey_do.events import (
    BaseEvent,
    ClickEvent,
    Events,
    KeyboardEvent,
    MouseButtonEvent,
    ScrollEvent,
    StateSnapshotEvent,
    WriteEvent,
)


def drop_consecutive_state_snapshots(events: Events) -> Events:
    return merge_consecutive_events(
        events,
        [drop_consecutive_state_snapshots_1],
    )


def drop_consecutive_state_snapshots_1(first_event: BaseEvent, second_event: BaseEvent) -> List[BaseEvent]:
    """If both events are snapshot events, keep only the second, otherwise return both."""
    if isinstance(first_event, StateSnapshotEvent) and isinstance(second_event, StateSnapshotEvent):
        return [second_event]
    return [first_event, second_event]


def convert_mouse_press_then_release_to_click(events: Events, max_seconds: float = 0.2, max_pixels: int = 5) -> Events:
    return merge_consecutive_events(
        events,
        [
            lambda e1, e2: merge_consecutive_mouse_press_then_release_to_click(
                e1, e2, max_seconds=max_seconds, max_pixels=max_pixels
            )
        ],
    )


def merge_consecutive_mouse_press_then_release_to_click(
    first_event: BaseEvent, second_event: BaseEvent, max_seconds: float = 0.2, max_pixels: int = 5
) -> List[BaseEvent]:
    """
    Convert a mouse press event followed by release event into a click event, as long as the events are consecutive,
    no more than ``max_seconds`` apart from each other, and the distance the mouse moved is no more than ``max_pixels``.

    The distance for mouse movement is computed using Euclidean distance.
    """
    if not isinstance(first_event, MouseButtonEvent) or not isinstance(second_event, MouseButtonEvent):
        return [first_event, second_event]

    if first_event.timestamp > second_event.timestamp:
        # Swap events so first_event comes first chronologically
        first_event, second_event = second_event, first_event

    if (
        first_event.button != second_event.button
        or first_event.action != "press"
        or second_event.action != "release"
        or (second_event.timestamp - first_event.last_timestamp_or_first).total_seconds() > max_seconds
        or first_event.location.distance_to(second_event.location) > max_pixels
    ):
        return [first_event, second_event]

    return [ClickEvent.from_mouse_button_event(first_event)]


def convert_mouse_clicks_to_multi_click(events: Events, max_seconds: float = 0.4, max_pixels: int = 5) -> Events:
    return merge_consecutive_events(
        events,
        [
            lambda e1, e2: merge_consecutive_mouse_clicks_to_multi_click(
                e1, e2, max_seconds=max_seconds, max_pixels=max_pixels
            )
        ],
    )


def merge_consecutive_mouse_clicks_to_multi_click(
    first_event: BaseEvent, second_event: BaseEvent, max_seconds: float = 0.4, max_pixels: int = 5
) -> List[BaseEvent]:
    """
    Convert sequential clicks of the same mouse button to a multi-click (e.g. double-click), as long as the subsequent
    click is at most ``max_seconds`` after the previous and the distance the mouse moved is no more than ``max_pixels``.

    The distance for mouse movement is computed using Euclidean distance.
    """
    if not isinstance(first_event, MouseButtonEvent) or not isinstance(second_event, MouseButtonEvent):
        return [first_event, second_event]

    if first_event.timestamp > second_event.timestamp:
        # Swap events so first_event comes first chronologically
        first_event, second_event = second_event, first_event

    if (
        first_event.button != second_event.button
        or first_event.action != "click"
        or second_event.action != "click"
        or (second_event.timestamp - first_event.last_timestamp_or_first).total_seconds() > max_seconds
        or first_event.location.distance_to(second_event.location) > max_pixels
    ):
        return [first_event, second_event]

    if not isinstance(first_event, ClickEvent):
        first_event = ClickEvent.from_mouse_button_event(first_event)

    if not isinstance(second_event, ClickEvent):
        second_event = ClickEvent.from_mouse_button_event(second_event)

    first_event = first_event.copy()
    first_event.update_with(second_event)

    return [first_event]


def convert_key_press_then_release_to_write(events: Events, max_seconds: float = 0.15) -> Events:
    return merge_consecutive_events(
        events, [lambda e1, e2: merge_consecutive_key_press_then_release_to_write(e1, e2, max_seconds=max_seconds)]
    )


def merge_consecutive_key_press_then_release_to_write(
    first_event: BaseEvent, second_event: BaseEvent, max_seconds: float = 0.15
) -> List[BaseEvent]:
    """
    Convert a key press event followed by release event into a write event, as long as the events are consecutive and
    no more than ``max_seconds`` apart from each other.
    """
    if not isinstance(first_event, KeyboardEvent) or not isinstance(second_event, KeyboardEvent):
        return [first_event, second_event]

    if first_event.timestamp > second_event.timestamp:
        # Swap events so first_event comes first chronologically
        first_event, second_event = second_event, first_event

    if (
        (second_event.timestamp - first_event.last_timestamp_or_first).total_seconds() > max_seconds
        or first_event.key != second_event.key
        or first_event.action != "press"
        or second_event.action != "release"
    ):
        return [first_event, second_event]

    return [WriteEvent.from_keyboard_event(first_event)]


def merge_consecutive_write_events(events: Events, max_seconds: float = 1) -> Events:
    return merge_consecutive_events(
        events, [lambda e1, e2: merge_consecutive_write_events_1(e1, e2, max_seconds=max_seconds)]
    )


def merge_consecutive_write_events_1(
    first_event: BaseEvent, second_event: BaseEvent, max_seconds: float = 1
) -> List[BaseEvent]:
    """
    Merge consecutive write events that are no more than ``max_seconds`` apart.
    """
    if not isinstance(first_event, WriteEvent) or not isinstance(second_event, WriteEvent):
        return [first_event, second_event]

    if first_event.timestamp > second_event.timestamp:
        # Swap events so first_event comes first chronologically
        first_event, second_event = second_event, first_event

    if (second_event.timestamp - first_event.last_timestamp_or_first).total_seconds() > max_seconds:
        return [first_event, second_event]

    event = first_event.copy(deep=True)
    event.update_with(second_event)
    return [event]


def merge_consecutive_scroll_events(
    first_event: BaseEvent,
    second_event: BaseEvent,
    max_seconds: float = 3,
    max_pixels: int = 5,
    merge_opposite_directions: bool = False,
) -> List[BaseEvent]:
    """
    Merge two scroll events that are no more than ``max_seconds`` apart and the distance the mouse moved is no
    more than ``max_pixels``.

    If ``merge_opposite_directions`` is False (default), then consecutive scroll events in opposite directions are not
    merged.  For example, if one event says to scroll -2 in the x direction and the next event is a scroll +1 in the x
    direction, then they will not be merged.  If ``merge_opposite_directions`` is True, then they will be merged to -1
    in the x direction.

    The distance for mouse movement is computed using Euclidean distance.
    """
    if not isinstance(first_event, ScrollEvent) or not isinstance(second_event, ScrollEvent):
        return [first_event, second_event]

    if first_event.timestamp > second_event.timestamp:
        # Swap events so first_event comes first chronologically
        first_event, second_event = second_event, first_event

    if (second_event.timestamp - first_event.last_timestamp_or_first).total_seconds() > max_seconds or (
        first_event.location.distance_to(second_event.location)
    ) > max_pixels:
        return [first_event, second_event]

    x_is_compatible = any(
        [
            first_event.scroll.dx == 0,
            second_event.scroll.dx == 0,
            math.copysign(1, first_event.scroll.dx) == math.copysign(1, second_event.scroll.dx),
        ]
    )
    y_is_compatible = any(
        [
            first_event.scroll.dy == 0,
            second_event.scroll.dy == 0,
            math.copysign(1, first_event.scroll.dy) == math.copysign(1, second_event.scroll.dy),
        ]
    )

    if merge_opposite_directions or (x_is_compatible and y_is_compatible):
        event = first_event.copy()
        event.update_with(second_event)
        return [event]
    return [first_event, second_event]


def merge_consecutive_events(
    events: Events, event_mergers: Iterable[Callable[[BaseEvent, BaseEvent], List[BaseEvent]]]
) -> Events:
    """
    Iterate over the events in ``event``, merging events according to the functions in ``event_mergers``.

    For example, given:
    * ``events`` being [event1, event2, event3, event4, event5]
    * ``event_mergers`` being:
        [function_merging_event1_event2_into_eventA, function_merging_eventA_event3_into_eventD,
        function_merging_event1_event2_into_eventB, function_merging_event2_event3_into_eventC,
        function_merging_eventD_event5_into_eventE]

    The result will be [eventD, event4, event5]
    """
    if len(events) < 2:
        return events

    final_events = [events[0]]
    for event in events[1:]:  # type: BaseEvent
        for merger in event_mergers:
            result_events = merger(final_events[-1], event)
            if len(result_events) == 1:
                # The events have been merged
                final_events[-1] = result_events[0]
                event = None
                break

        if event is not None:
            final_events.append(event)
    return Events.from_iterable(final_events)


ALL_SIMPLIFIERS = (
    drop_consecutive_state_snapshots,
    convert_mouse_press_then_release_to_click,
    convert_mouse_clicks_to_multi_click,
    convert_key_press_then_release_to_write,
    merge_consecutive_write_events,
    merge_consecutive_scroll_events,
)


def run_simplifiers(events: Events, simplifiers: List[Callable[[Events], Events]] = ALL_SIMPLIFIERS) -> Events:
    for simplifier in simplifiers:
        events = simplifier(events)
    return events
