"""Test application of identities"""
from datetime import datetime, timedelta

import pytz

from gpsdio_segment.core import Segmentizer
from gpsdio_segment.msg_processor import Identity


class _MsgGenerator(object):
    def __init__(self, interval=timedelta(minutes=4)):
        self._timestamp = datetime.utcnow().replace(tzinfo=pytz.UTC)
        self._msgid = 1
        self._interval = interval

    def make_position_message(self):
        msg = {
            "msgid": self._msgid,
            "ssvid": 1,
            "lat": 0,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": self._timestamp,
            "course": 0,
            "speed": 0,
        }
        self._timestamp += self._interval
        self._msgid += 1
        return msg

    def make_identity_message(self, shipname="boatymcboatface"):
        msg = {
            "msgid": self._msgid,
            "ssvid": 1,
            "type": "AIS.5",
            "timestamp": self._timestamp,
            "shipname": shipname,
        }
        self._timestamp += self._interval
        self._msgid += 1
        return msg


def test_identity_before():
    gen = _MsgGenerator()
    messages = []
    messages.append(gen.make_identity_message())
    for i in range(20):
        messages.append(gen.make_position_message())

    segments = [x for x in Segmentizer(messages) if not x.noise]

    assert len(segments) == 1
    identities = [x["identities"] for x in segments[0].msgs]
    for i in range(3):
        assert len(identities[i]) == 1
        assert identities[i] == {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1
        }
    for i in range(3, 20):
        assert identities[i] == {}


def test_identity_after():
    gen = _MsgGenerator()
    messages = []
    for i in range(20):
        messages.append(gen.make_position_message())
    messages.append(gen.make_identity_message())

    segments = [x for x in Segmentizer(messages) if not x.noise]

    assert len(segments) == 1
    identities = [x["identities"] for x in segments[0].msgs]
    for i in range(17):
        assert identities[i] == {}
    for i in range(17, 20):
        assert len(identities[i]) == 1
        assert identities[i] == {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1
        }


def test_multiple_identities():
    gen = _MsgGenerator()
    messages = []
    for i in range(6):
        messages.append(gen.make_position_message())
    messages.append(gen.make_identity_message())
    messages.append(gen.make_position_message())
    messages.append(gen.make_position_message())
    messages.append(gen.make_position_message())
    messages.append(gen.make_identity_message())
    messages.append(gen.make_position_message())
    messages.append(gen.make_position_message())
    messages.append(gen.make_position_message())
    messages.append(gen.make_identity_message("samiam"))
    for i in range(6):
        messages.append(gen.make_position_message())

    segments = [x for x in Segmentizer(messages) if not x.noise]

    assert len(segments) == 1
    identities = [x["identities"] for x in segments[0].msgs]

    assert identities == [
        {},
        {},
        {},
        {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1
        },
        {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1
        },
        {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1
        },
        {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 2
        },
        {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 2
        },
        {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 2
        },
        {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1,
            Identity(
                shipname="samiam",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1,
        },
        {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1,
            Identity(
                shipname="samiam",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1,
        },
        {
            Identity(
                shipname="boatymcboatface",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1,
            Identity(
                shipname="samiam",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1,
        },
        {
            Identity(
                shipname="samiam",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1
        },
        {
            Identity(
                shipname="samiam",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1
        },
        {
            Identity(
                shipname="samiam",
                callsign=None,
                imo=None,
                transponder_type="AIS-A",
                length=None,
                width=None,
            ): 1
        },
        {},
        {},
        {},
    ]
