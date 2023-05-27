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
    """If there are consecutive snapshot events, keep only the last one."""
    reversed_saved_events = []
    for event in reversed(events):
        if len(reversed_saved_events) == 0:
            reversed_saved_events.append(event)
        elif isinstance(event, StateSnapshotEvent):
            if not isinstance(reversed_saved_events[-1], StateSnapshotEvent):
                reversed_saved_events.append(event)
        else:
            reversed_saved_events.append(event)

    return Events.from_iterable(reversed(reversed_saved_events))


def convert_mouse_press_then_release_to_click(events: Events, max_seconds: float = 0.2, max_pixels: int = 5) -> Events:
    """
    Convert a mouse press event followed by release event into a click event, as long as the events are consecutive,
    no more than ``max_seconds`` apart from each other, and the distance the mouse moved is no more than ``max_pixels``.

    The distance for mouse movement is computed using Euclidean distance.
    """
    new_events = []
    for event in events:
        if (
            len(new_events) > 0
            and isinstance(event, MouseButtonEvent)
            and isinstance(new_events[-1], MouseButtonEvent)
            and new_events[-1].button == event.button
            and new_events[-1].action == "press"
            and event.action == "release"
            and (event.timestamp - new_events[-1].timestamp).total_seconds() <= max_seconds
            and (event.location.distance_to(new_events[-1].location)) <= max_pixels
        ):
            new_events[-1] = ClickEvent.from_mouse_button_event(new_events[-1])
        else:
            new_events.append(event)

    return Events.from_iterable(new_events)


def convert_mouse_clicks_to_multi_click(events: Events, max_seconds: float = 0.4, max_pixels: int = 5) -> Events:
    """
    Convert sequential clicks of the same mouse button to a multi-click (e.g. double-click), as long as the subsequent
    click is at most ``max_seconds`` after the previous and the distance the mouse moved is no more than ``max_pixels``.

    The distance for mouse movement is computed using Euclidean distance.
    """
    reversed_saved_events = []
    for event in reversed(events):
        if (
            len(reversed_saved_events) > 0
            and isinstance(event, (MouseButtonEvent, ClickEvent))
            and isinstance(reversed_saved_events[-1], (MouseButtonEvent, ClickEvent))
            and reversed_saved_events[-1].button == event.button
            and reversed_saved_events[-1].action == "click"
            and event.action == "click"
            and (reversed_saved_events[-1].timestamp - event.last_timestamp_or_first).total_seconds() <= max_seconds
            and (event.location.distance_to(reversed_saved_events[-1].location)) <= max_pixels
        ):
            next_event = reversed_saved_events[-1]
            if not isinstance(next_event, ClickEvent):
                next_event = ClickEvent.from_mouse_button_event(next_event)

            if not isinstance(event, ClickEvent):
                event = ClickEvent.from_mouse_button_event(event)
            else:
                event = event.copy()

            event.update_with(next_event)

            reversed_saved_events[-1] = event
        else:
            reversed_saved_events.append(event)

    return Events.from_iterable(reversed(reversed_saved_events))


def convert_key_press_then_release_to_write(events: Events, max_seconds: float = 0.15) -> Events:
    """
    Convert a key press event followed by release event into a write event, as long as the events are consecutive and
    no more than ``max_seconds`` apart from each other.
    """
    new_events = []
    for event in events:
        if (
            len(new_events) > 0
            and isinstance(event, KeyboardEvent)
            and isinstance(new_events[-1], KeyboardEvent)
            and new_events[-1].key == event.key
            and new_events[-1].action == "press"
            and event.action == "release"
            and (event.timestamp - new_events[-1].timestamp).total_seconds() <= max_seconds
        ):
            new_events[-1] = WriteEvent.from_keyboard_event(new_events[-1])
        else:
            new_events.append(event)

    return Events.from_iterable(new_events)


def merge_consecutive_write_events(events: Events, max_seconds: float = 1) -> Events:
    """
    Merge consecutive write events that are no more than ``max_seconds`` apart.
    """
    reversed_saved_events = []
    for event in reversed(events):
        if (
            len(reversed_saved_events) > 0
            and isinstance(event, WriteEvent)
            and isinstance(reversed_saved_events[-1], WriteEvent)
            and (reversed_saved_events[-1].timestamp - event.last_timestamp_or_first).total_seconds() <= max_seconds
        ):
            next_event = reversed_saved_events[-1]
            event = event.copy(deep=True)
            event.append(next_event)
            reversed_saved_events[-1] = event
        else:
            reversed_saved_events.append(event)

    return Events.from_iterable(reversed(reversed_saved_events))


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
