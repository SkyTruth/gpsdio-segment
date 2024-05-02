import itertools
from datetime import datetime
from datetime import timedelta

from support import utcify

from gpsdio_segment.segmenter import Segmenter
from gpsdio_segment.segment import Segment, SegmentState
from gpsdio_segment.msg_processor import (INFO_ONLY_MESSAGE, POSITION_MESSAGE,
                                          MsgProcessor)
from gpsdio_segment.matcher import Matcher


def _annotate(messages, timestamp=datetime.now(), msgid=1, ssvid=10):
    interval = timedelta(minutes=1)

    for message in messages:
        message['timestamp'] = message.get('timestamp', timestamp)
        message['msgid'] = message.get('msgid', msgid)
        message['ssvid'] = message.get('ssvid', ssvid)
        yield utcify(message)
        msgid += 1
        timestamp += interval

def test_stateful():
    now = datetime.now()
    ssvid = 10
    messages1 = [
        {
            "type": "AIS.1",
            "lat": 0,
            "lon": 0,
            "course": 0,
            "speed": 1,
        },
        {
            "type": "AIS.5",
            "shipname": "Argus"
        },
    ]
    messages1 = list(_annotate(messages1))

    max_hours = Matcher.max_hours
    matcher = Matcher(max_hours=max_hours, ssvid=ssvid)
    msg_processor = MsgProcessor(matcher.very_slow, ssvid)

    segmenter1 = Segmenter(messages1, ssvid=ssvid, max_hours=max_hours, matcher=matcher, msg_processor=msg_processor)
    states = []
    seg_ids = set()
    for seg in segmenter1:
        if not seg.closed:
            states.append(seg.state)
            seg_ids.add(seg.id)

    assert len(states) == 1

    messages2 = [
        {
            "type": "AIS.1",
            "lat": 0.001,
            "lon": 0.001,
            "course": 0,
            "speed": 1,
        },
    ]
    messages2 = list(_annotate(messages2, timestamp=now + timedelta(hours=1), msgid=100, ssvid=ssvid))

    segmenter2 = Segmenter.from_seg_states(seg_states=states,
                                          instream=messages2,
                                          max_hours=max_hours,
                                          matcher=matcher,
                                          msg_processor=msg_processor,
                                          ssvid=ssvid)
    for seg in segmenter2:
        if not seg.closed:
            seg_ids.add(seg.id)

    # position from messages2 is in the same segment as position from messages1
    assert len(seg_ids) == 1

