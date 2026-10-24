"""Vector's spoken lines.

Every category is a "shuffle bag": lines come out in random order and none repeats until the
whole bag has been used (and the first line of a new round is never the last one of the old
round), so Vector doesn't sound like a recording.

Placeholders:  {title} -> "sir"   {Title} -> "Sir"   plus whatever pick() is given
               ({label}, {percent}, {hour}, {hours}).
To add a line, just add a string to the right list below.
"""
import random
from datetime import datetime

import config

POOLS: dict[str, list[str]] = {
    # said once when Vector starts
    "startup": [
        "Online and fully operational, {title}.",
        "Systems nominal. Awaiting instructions.",
        "At your service, {title}.",
        "Vector online, {title}.",
    ],
    # first launch of the day (any time except the morning, see startup_line)
    "welcome_home": [
        "Welcome home, {title}.",
    ],
    # first launch of the day, between 5 AM and noon
    "morning": [
        "Good morning, {title}. Shall I run through the day's agenda?",
    ],
    # after "Hey Vector" with nothing else said
    "wake": [
        "At your service, {title}.",
        "For you, {title}, always.",
        "Yes, {title}?",
    ],
    # a quick action went through (open app, volume, media...) or the model said nothing
    "done": [
        "As always, {title}, a great pleasure.",
        "Will do, {title}.",
        "Consider it done.",
        "Already in progress, {title}.",
        "Done, {title}.",
    ],
    # something went wrong
    "fail": [
        "I'm afraid that's beyond my current reach, {title}.",
        "My apologies, {title}. That didn't go as planned.",
    ],
    # no brain reachable
    "offline": [
        "My connection to the network seems to be down, {title}.",
    ],
    # proactive lines (see monitor() in vector.py)
    "late_night": [
        "It's past {hour}, {title}. I'd suggest sleep, though I know you won't.",
    ],
    "break_nudge": [
        "{Title}, you've been at this for {hours}. A short break might do you good.",
        "{hours} on the clock, {title}. Perhaps some light stretching?",
        "I admire the dedication, {title}, but it has been {hours}. Your posture is becoming concerning.",
    ],
    "low_battery": [
        "Power reserves at {percent} percent, {title}. Might I suggest a charger?",
        "Battery is down to {percent} percent, {title}. I'd plug in soon.",
    ],
    "timer_done": [
        "Your {label} is done, {title}.",
        "{Title}, your {label} has finished.",
    ],
    "shutdown": [
        "Powering down. Do try not to miss me, {title}.",
        "Standing by, {title}.",
        "Goodbye, {title}.",
    ],
}


class _Bag:
    def __init__(self, items: list[str]):
        self.items = list(items)
        self.queue: list[str] = []
        self.last: str | None = None

    def next(self) -> str:
        if not self.queue:
            self.queue = self.items[:]
            random.shuffle(self.queue)
            # pop() takes from the end, so keep the old round's last line from opening the new one
            if len(self.queue) > 1 and self.queue[-1] == self.last:
                self.queue[0], self.queue[-1] = self.queue[-1], self.queue[0]
        self.last = self.queue.pop()
        return self.last


_bags = {name: _Bag(items) for name, items in POOLS.items()}


def pick(category: str, **fmt) -> str:
    """Return the next line from a category, with placeholders filled in."""
    title = config.USER_TITLE
    return _bags[category].next().format(title=title, Title=title.capitalize(), **fmt)


# ---------- helpers for the time-aware lines ----------
def hour_phrase(hour: int) -> str:
    if hour == 0:
        return "midnight"
    return f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"


def duration_phrase(seconds: float) -> str:
    minutes = round(seconds / 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = round(seconds / 3600)
    return f"{hours} hour{'s' if hours != 1 else ''}"


def startup_line(first_launch_today: bool, now: datetime | None = None) -> str:
    now = now or datetime.now()
    if first_launch_today:
        return pick("morning") if 5 <= now.hour < 12 else pick("welcome_home")
    return pick("startup")