import datetime
from itertools import groupby

import pytest

from gpsdio_segment.core import Segmentizer


class MessageGenerator(object):
    def __init__(self, mmsi=None):
        self.mmsi = mmsi if mmsi else 123456789
        self.reset()

    def reset(self):
        self.timestamp = datetime.datetime.now()
        self.lat = 0
        self.lon = 0
        self.index = 0

    def increment(self):
        self.timestamp += datetime.timedelta(hours=1)
        self.lat += 0.01
        self.lon += 0.01
        self.index += 1

    def next_msg(self):
        self.increment()
        return {"mmsi": self.mmsi, "idx": self.index, "timestamp": self.timestamp}

    def next_posit_msg(self):
        self.increment()
        return {"mmsi": self.mmsi, "lat": self.lat, "lon": self.lon}

    def next_time_posit_msg(self):
        self.increment()
        return {
            "mmsi": self.mmsi,
            "lat": self.lat,
            "lon": self.lon,
            "timestamp": self.timestamp,
        }

    def next_msg_from_stub(self, stub):
        self.increment()
        msg = dict(idx=self.index, mmsi=self.mmsi, timestamp=self.timestamp)
        seg = stub.get("seg", 0)
        type = stub.get("type", 99)
        if type in (1, 3, 18, 19):
            msg["lat"] = self.lat - (seg * 2)
            msg["lon"] = self.lon - (seg * 2)
            msg["speed"] = 0.6
            msg["course"] = 45
        msg.update(stub)

        return msg

    def generate_messages(self, message_stubs):
        self.reset()
        for stub in message_stubs:
            yield self.next_msg_from_stub(stub)

    def assert_segments(self, message_stubs, label="None"):
        messages = list(self.generate_messages(message_stubs))
        segments = list(Segmentizer(messages))

        # group the input messages into exected segment groups based on the 'seg' field
        sorted_messages = sorted(messages, key=lambda x: x["seg"])
        grouped_messages = groupby(sorted_messages, key=lambda x: x["seg"])
        expected_seg_messages = [
            set(m["idx"] for m in msgs) for _, msgs in grouped_messages
        ]

        # put segments in time order and extract message indexes
        sorted_segments = sorted(segments, key=lambda x: x.temporal_extent)
        actual_seg_messages = [set(m["idx"] for m in seg) for seg in sorted_segments]

        # compare the sets of message indexes in the actual and expected segment groups
        assert len(actual_seg_messages) == len(expected_seg_messages)
        for actual, expected in zip(actual_seg_messages, expected_seg_messages):
            assert actual == expected


@pytest.fixture(scope="function")
def msg_generator():
    return MessageGenerator()


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
