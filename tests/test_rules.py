"""
Unittests for specific segmentation rules.
"""


from datetime import datetime, timedelta

from support import utcify

from gpsdio_segment.core import Segmentizer
from gpsdio_segment.discrepancy import DiscrepancyCalculator


# deltas = [{'distance': 0, 'speed': 0, 'duration': 0}]
# distances are in nautical miles
# speeds are in knots
# durations are in hours
# specify 2 of the 3 possible values
def generate_messages_from_deltas(deltas):
    msg = {"ssvid": 1, "lat": 0, "lon": 0, "timestamp": datetime.now()}
    yield msg
    for d in deltas:
        distance = d.get("distance") or d["speed"] * d["duration"]
        duration = d.get("duration") or d["speed"] / d["distance"]
        lon = msg["lon"] + (distance / 60.0)
        ts = msg["timestamp"] + timedelta(hours=duration)
        speed = d["speed"] if ("speed" in d) else d["distance"] / d["duration"]
        msg = dict(
            ssvid=msg["ssvid"],
            lat=msg["lat"],
            lon=lon,
            timestamp=ts,
            speed=speed,
            course=0,
        )
        yield msg


def test_two_different_ssvid():
    # If a second different ssvid is encountered it should be ignored
    # Should produce a single segment containing a single point
    p1 = {
        "ssvid": 1,
        "lat": 0,
        "lon": 0,
        "type": "UNKNOWN",
        "timestamp": datetime.now(),
        "course": 0,
        "speed": 0,
    }
    p2 = {
        "ssvid": 2,
        "lat": 0.0000001,
        "lon": 0.0000001,
        "type": "UNKNOWN",
        "timestamp": datetime.now(),
        "course": 0,
        "speed": 0,
    }
    segmenter = Segmentizer([utcify(x) for x in [p1, p2]])
    segments = list(segmenter)

    # Should produce a single segment containing a single point
    assert len(segments) == 1
    for seg in segments:
        assert len(seg) == 1


def test_good_speed_good_time():
    # Make sure two points within the max_hours and max_speed are in the same segment
    p1 = {
        "msgid": 1,
        "ssvid": 1,
        "lat": 0,
        "lon": 0,
        "type": "UNKNOWN",
        "timestamp": datetime.now(),
        "course": 0,
        "speed": 5,
    }
    p2 = {
        "msgid": 2,
        "ssvid": 1,
        "lat": 1,
        "lon": 0,
        "type": "UNKNOWN",
        "timestamp": p1["timestamp"] + timedelta(hours=3),
        "course": 0,
        "speed": 5,
    }
    msgs = [utcify(x) for x in [p1, p2]]
    segmenter = Segmentizer(msgs)
    segments = list(segmenter)

    # Should produce a single segment with two points
    hours = DiscrepancyCalculator.compute_msg_delta_hours(p1, p2)
    discrepancy = segmenter._matcher.compute_discrepancy(p1, p2)
    assert discrepancy / hours <= segmenter.max_knots
    assert len(segments) == 1
    for seg in segments:
        assert len(seg) == 2


# TODO: add tests of new segmenter rules
