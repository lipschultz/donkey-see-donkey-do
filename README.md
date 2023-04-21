# Donkey See, Donkey Do

An application that watches what you do on your computer and creates a script that can replay those behaviors in the future.


## Usage

```python
from donkey_see_donkey_do.events import Events
from donkey_see_donkey_do.recorder import Recorder

recorder = Recorder()
recorder.record()
# interact with the computer, clicking on things, typing stuff in, etc.
recorder.stop()

events = recorder.get_events()

with open("events.json", "w") as fp:
    fp.write(events.json())

loaded_events = Events.parse_file("events.json")

loaded_events.replay()
```
