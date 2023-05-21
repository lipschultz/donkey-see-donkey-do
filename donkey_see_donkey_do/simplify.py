from donkey_see_donkey_do.events import (
    ClickEvent,
    Events,
    KeyboardEvent,
    MouseButtonEvent,
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
            and (reversed_saved_events[-1].timestamp - event.timestamp).total_seconds() <= max_seconds
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
