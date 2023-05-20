from donkey_see_donkey_do.events import ClickEvent, Events, MouseButtonEvent, StateSnapshotEvent


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
