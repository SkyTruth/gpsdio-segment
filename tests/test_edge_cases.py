"""
Tests for weird edge cases.
"""


from collections import Counter
from datetime import datetime, timedelta

from gpsdio_segment.core import Segmentizer
from gpsdio_segment.msg_processor import MsgProcessor
from support import utcify


def test_first_is_non_posit():
    pass


def test_same_point_same_time():
    msg1 = {
        "ssvid": 100,
        "msgid": 1,
        "lat": 10,
        "lon": 10,
        "type": "UNKNOWN",
        "timestamp": datetime.now(),
        "course": 0,
        "speed": 1,
    }
    msg2 = msg1.copy()
    msg2["msgid"] = 2
    messages = [msg1, msg2]
    messages = [utcify(x) for x in messages]
    segments = list(Segmentizer(messages))
    assert len(segments) == 1
    for seg in segments:
        assert len(seg) == 1


def test_same_point_absurd_timedelta():
    msg1 = {
        "ssvid": 10000,
        "msgid": 1,
        "lat": -90,
        "lon": -90,
        "type": "UNKNOWN",
        "timestamp": datetime.now(),
        "course": 0,
        "speed": 1,
    }
    msg2 = {
        "ssvid": 10000,
        "msgid": 2,
        "lat": -90,
        "lon": -90,
        "type": "UNKNOWN",
        "timestamp": msg1["timestamp"] + timedelta(days=1000),
        "course": 1,
        "speed": 1,
    }
    messages = [msg1, msg2]
    messages = [utcify(x) for x in messages]
    segments = list(Segmentizer(messages))
    assert len(segments) == 2
    for seg in segments:
        assert len(seg) == 1


def test_same_time_absurd_distance():
    t = datetime.now()
    msg1 = {
        "ssvid": 10000,
        "msgid": 1,
        "lat": 0,
        "lon": 0,
        "type": "UNKNOWN",
        "timestamp": t,
        "course": 0,
        "speed": 1,
    }
    msg2 = {
        "ssvid": 10000,
        "msgid": 2,
        "lat": 10,
        "lon": 10,
        "type": "UNKNOWN",
        "timestamp": t,
        "course": 1,
        "speed": 1,
    }
    messages = [msg1, msg2]
    messages = [utcify(x) for x in messages]
    segments = list(Segmentizer(messages))
    assert len(segments) == 2
    for seg in segments:
        assert len(seg) == 1


def test_with_non_posit():
    # Non-positional messages are emitted as there own segments
    # This should produce two segments, each with 3 points - two of which are
    # positional and 1 that is a non-posit

    # Continuous
    msg1 = {
        "idx": 0,
        "msgid": 1,
        "ssvid": 1,
        "lat": 0,
        "lon": 0,
        "type": "AIS.1",
        "timestamp": datetime.now(),
        "course": 0,
        "speed": 1,
    }
    msg2 = {
        "idx": 1,
        "msgid": 2,
        "ssvid": 1,
        "type": "AIS.1",
        "timestamp": msg1["timestamp"] + timedelta(hours=1),
    }
    msg3 = {
        "idx": 2,
        "msgid": 3,
        "ssvid": 1,
        "lat": 0.00001,
        "lon": 0.00001,
        "type": "AIS.1",
        "timestamp": msg1["timestamp"] + timedelta(hours=2),
        "course": 0,
        "speed": 1,
    }

    # Also continuous but not to the previous trio
    msg4 = {
        "idx": 3,
        "msgid": 4,
        "ssvid": 1,
        "lat": 65,
        "lon": 65,
        "type": "AIS.1",
        "timestamp": msg3["timestamp"] + timedelta(days=100),
        "course": 0,
        "speed": 1,
    }
    msg5 = {
        "idx": 4,
        "msgid": 5,
        "ssvid": 1,
        "type": "AIS.1",
        "timestamp": msg4["timestamp"] + timedelta(hours=1),
    }
    msg6 = {
        "idx": 5,
        "msgid": 6,
        "ssvid": 1,
        "lat": 65.00001,
        "lon": 65.00001,
        "type": "AIS.1",
        "timestamp": msg4["timestamp"] + timedelta(hours=2),
        "course": 0,
        "speed": 1,
    }

    messages = [msg1, msg2, msg3, msg4, msg5, msg6]
    messages = [utcify(x) for x in messages]

    segments = list(Segmentizer(messages))
    assert len(segments) == 4
    assert [len(seg) for seg in segments] == [1, 2, 1, 2]


def test_with_non_posit_first():
    """
    non-pos message added first should be emitted as single message noise segment
    """
    messages = [
        {
            "ssvid": 1,
            "msgid": 1,
            "timestamp": datetime(2015, 1, 1, 1, 1, 1),
            "type": "AIS.1",
        },
        {
            "ssvid": 1,
            "msgid": 2,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 1),
            "course": 0,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 3,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 2, 1, 1),
            "course": 1,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 4,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 4, 1, 1),
            "course": 2,
            "speed": 1,
        },
    ]
    messages = [utcify(x) for x in messages]

    segs = list(Segmentizer(messages))
    assert len(segs) == 2


def test_first_message_out_of_bounds():

    """
    If the first input message has a location that is completely off the map,
    we need to make sure that it doesn't end up inside the internal segment
    container.
    """

    messages = [
        {
            "ssvid": 1,
            "msgid": 1,
            "lat": 91,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 1),
            "course": 0,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 2,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 1),
            "course": 1,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 3,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 2, 1, 1),
            "course": 2,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 4,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 4, 1, 1),
            "course": 3,
            "speed": 1,
        },
    ]
    messages = [utcify(x) for x in messages]

    output = list(Segmentizer(messages))
    assert len(output) == 2

    # Should get one bad segment and one good segment
    # Bad segment should just have the first message
    bs, s = output
    assert len(bs) == 1
    assert bs.msgs == messages[:1]

    # Good segment should have the rest of the messages
    assert len(s) == 3
    assert s.msgs == messages[1:]


def test_first_message_out_of_bounds_gt_24h():
    """
    Out of bounds location as the first message after all previous segments
    have been cleared. Should put the bad message in a BadSegment and continue
    with the next good message
    """

    messages = [
        {
            "ssvid": 1,
            "msgid": 1,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 1),
            "course": 0,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 2,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 2),
            "course": 1,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 3,
            "lat": None,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 10, 1, 1, 1),
            "course": 2,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 4,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 10, 1, 1, 2),
            "course": 3,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 5,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 10, 1, 1, 3),
            "course": 4,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 6,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 10, 1, 1, 4),
            "course": 5,
            "speed": 1,
        },
    ]
    messages = [utcify(x) for x in messages]

    segs = list(Segmentizer(messages))
    assert Counter([seg.__class__.__name__ for seg in segs]) == {
        "Segment": 1,
        "ClosedSegment": 1,
        "BadSegment": 1,
    }


def test_non_pos_first_followed_by_out_of_bounds():
    """
    When a non-pos message is first, it gets emitted as a singleton segment,
    and then when a message with a bad location comes along
    it gets emitted as noise. Then a real segment is created.
    """
    messages = [
        {
            "ssvid": 1,
            "msgid": 1,
            "timestamp": datetime(2015, 1, 1, 1, 1, 1),
            "type": "AIS.1",
        },
        {
            "ssvid": 1,
            "msgid": 2,
            "lat": None,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 1),
            "course": 0,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 3,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 2),
            "course": 1,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 4,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 3),
            "course": 2,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 5,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 4),
            "course": 3,
            "speed": 1,
        },
    ]
    messages = [utcify(x) for x in messages]

    segs = list(Segmentizer(messages))
    assert Counter([seg.__class__.__name__ for seg in segs]) == {
        "InfoSegment": 1,
        "BadSegment": 1,
        "Segment": 1,
    }


def test_bad_message_in_stream():

    messages = [
        {
            "ssvid": 1,
            "msgid": 1,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 1),
            "course": 0,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 2,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 4, 1, 1),
            "course": 1,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 3,
            "lat": None,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 7, 1, 1),
            "course": 2,
            "speed": 1,
        },
        {
            "ssvid": 1,
            "msgid": 4,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 7, 1, 1),
            "course": 3,
            "speed": 1,
        },
    ]
    messages = [utcify(x) for x in messages]

    # Should get one bad segment and one good segment
    new_msgs = list(Segmentizer(messages))
    bs, s = new_msgs

    assert len(s) == 3
    assert s.msgs == messages[:2] + messages[3:]

    assert len(bs) == 1
    assert bs.msgs == [messages[2]]


def test_isssue_24_prev_state_nonpos_msg_gt_max_hours():

    messages1 = [
        {
            "ssvid": 1,
            "lat": 89,
            "lon": 0,
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 1, 1, 1, 1),
            "course": 0,
            "speed": 1,
        }
    ]
    messages1 = [utcify(x) for x in messages1]

    messages2 = [
        {
            "ssvid": 1,
            "shipname": "Boaty",
            "type": "AIS.1",
            "timestamp": datetime(2015, 1, 9, 1, 1, 1),
        }
    ]
    messages2 = [utcify(x) for x in messages2]

    seg_states = [
        seg.state
        for seg in Segmentizer.from_seg_states(seg_states=[], instream=messages1)
    ]

    # these two should should produce the same result
    seg_msg_count1 = [
        len(seg.msgs)
        for seg in list(
            Segmentizer.from_seg_states(seg_states=seg_states, instream=messages2)
        )
    ]
    seg_msg_count2 = [
        len(seg.msgs)
        for seg in Segmentizer.from_seg_states(
            seg_states=seg_states, instream=messages2
        )
    ]

    expected = [1, 0]
    assert expected == seg_msg_count1
    assert expected == seg_msg_count2


def test_duplicate_msgid():
    msg1 = {
        "ssvid": 1,
        "msgid": 0,
        "lat": 21.42061667,
        "lon": -91.77805,
        "type": "AIS.1",
        "timestamp": datetime(2016, 5, 1, 0, 31, 27),
        "course": 0,
        "speed": 1,
    }
    msg2 = {
        "ssvid": 1,
        "msgid": 0,
        "lat": 21.45295,
        "lon": -91.80513333,
        "type": "AIS.1",
        "timestamp": datetime(2016, 5, 1, 1, 31, 27),
        "course": 0,
        "speed": 1,
    }
    msgs = []
    for i in range(4):
        m = msg1.copy()
        m["msgid"] += 0
        m["course"] += i
        msgs.append(m)
    msgs.append(msg2)
    msgs = [utcify(x) for x in msgs]
    segments = list(Segmentizer(msgs))
    assert len(segments) == 1
    for seg in segments:
        assert len(seg) == 1


def test_duplicate_pos_msg():
    msg1 = {
        "ssvid": 1,
        "msgid": 1,
        "lat": 21.42061667,
        "lon": -91.77805,
        "type": "AIS.1",
        "timestamp": datetime(2016, 5, 1, 0, 31, 27),
        "course": 0,
        "speed": 1,
    }
    msg2 = {
        "ssvid": 1,
        "msgid": 0,
        "lat": 21.45295,
        "lon": -91.80513333,
        "type": "AIS.1",
        "timestamp": datetime(2016, 5, 1, 1, 31, 27),
        "course": 0,
        "speed": 0,
    }
    msgs = []
    for i in range(4):
        m = msg1.copy()
        m["msgid"] += i
        msgs.append(m)
    msgs.append(msg2)
    msgs = [utcify(x) for x in msgs]
    segments = list(Segmentizer(msgs))
    assert len(segments) == 1
    for seg in segments:
        assert len(seg) == 2


def test_duplicate_pos_msg_zero_speed():
    msg1 = {
        "ssvid": 1,
        "msgid": 1,
        "lat": 21.42061667,
        "lon": -91.77805,
        "type": "AIS.1",
        "timestamp": datetime(2016, 5, 1, 0, 31, 27),
        "course": 0,
        "speed": 0,
    }
    msg2 = {
        "ssvid": 1,
        "msgid": 0,
        "lat": 21.45295,
        "lon": -91.80513333,
        "type": "AIS.1",
        "timestamp": datetime(2016, 5, 1, 1, 31, 27),
        "course": 0,
        "speed": 0,
    }
    msgs = []
    for i in range(4):
        m = msg1.copy()
        m["msgid"] += i
        msgs.append(m)
    msgs.append(msg2)
    msgs = [utcify(x) for x in msgs]
    segments = list(Segmentizer(msgs))
    assert len(segments) == 1
    for seg in segments:
        assert len(seg) == 5


def test_duplicate_ts_multiple_segs():
    # example from ssvid 316004240 2018-05-18 to 2018-05-19
    # 2 segments present because of a noise position in idx=1
    # so we have 2 segments [0,2,3,4] and [1] .
    messages = [
        {
            "idx": 0,
            "msgid": 0,
            "ssvid": 1,
            "lat": 44.63928,
            "lon": -63.551333,
            "type": "AIS.1",
            "timestamp": datetime(2018, 5, 18, 10, 0, 0),
            "course": 0,
            "speed": 0,
        },
        {
            "idx": 1,
            "msgid": 1,
            "ssvid": 1,
            "lat": 44.63928,
            "lon": -64.551334,
            "type": "AIS.1",
            "timestamp": datetime(2018, 5, 18, 10, 0, 0),
            "course": 0,
            "speed": 0,
        },
        {
            "idx": 2,
            "msgid": 2,
            "ssvid": 1,
            "lat": 44.63896,
            "lon": -63.551333,
            "type": "AIS.1",
            "timestamp": datetime(2018, 5, 18, 12, 0, 0),
            "course": 180,
            "speed": 0,
        },
        {
            "idx": 3,
            "msgid": 3,
            "ssvid": 1,
            "lat": 44.63928,
            "lon": -63.551333,
            "type": "AIS.1",
            "timestamp": datetime(2018, 5, 18, 14, 0, 0),
            "course": 0,
            "speed": 0,
        },
        {
            "idx": 4,
            "msgid": 4,
            "ssvid": 1,
            "lat": 44.63928,
            "lon": -63.551334,
            "type": "AIS.1",
            "timestamp": datetime(2018, 5, 18, 16, 0, 0),
            "course": 0,
            "speed": 0,
        },
    ]
    messages = [utcify(x) for x in messages]
    segments = list(Segmentizer(messages))
    assert [[0, 2, 3, 4], [1]] == sorted(
        [sorted({msg["idx"] for msg in seg}) for seg in segments]
    )
