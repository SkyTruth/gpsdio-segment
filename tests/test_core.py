"""
Unittests for gpsdio_segment.core
"""


from __future__ import division

import datetime

import gpsdio_segment.core


def test_segmentizer_attrs():
    # Attributes that are not called during processing
    segmenter = gpsdio_segment.core.Segmentizer([])
    assert segmenter.__class__.__name__ in repr(segmenter)


def test_segment_attrs():
    seg = gpsdio_segment.core.Segment(1, 123456789)

    # Segment is empty
    assert seg.ssvid == 123456789
    assert seg.id == 1
    assert len(seg) == 0
    assert seg.last_msg is None

    # Add some data
    msg1 = {"ssvid": 123456789, "field": 100}
    msg2 = {"ssvid": 123456789, "field": 100000}
    msg_with_point1 = {"ssvid": 123456789, "lat": 1, "lon": 1}
    msg_with_point2 = {"ssvid": 123456789, "lat": 10, "lon": 10}

    seg.add_msg(msg1)
    seg.add_msg(msg2)
    assert len(seg) == 2 == len(seg.msgs)
    assert seg.last_msg == msg2

    seg.add_msg(msg_with_point1)
    seg.add_msg(msg_with_point2)
    assert len(seg) == 4 == len(seg.msgs)

    expected_msgs = [msg1, msg2, msg_with_point1, msg_with_point2]
    for e, a in zip(expected_msgs, seg):
        print(e)
        print(a)
        assert e == a

    passed = False
    for e, a in zip(expected_msgs, seg):
        passed = True
        assert e == a
    assert passed

    assert "4" in repr(seg)
    assert "Segment" in repr(seg)


def test_last_msg_combinations():

    non_posit = {"ssvid": 1}
    posit = {"ssvid": 1, "lat": 2, "lon": 3}
    time_posit = {"ssvid": 1, "lat": 2, "lon": 3, "timestamp": datetime.datetime.now()}

    seg = gpsdio_segment.core.Segment(0, ssvid=1)
    assert seg.last_msg is None

    seg.add_msg(non_posit)
    assert seg.last_msg == non_posit

    seg.add_msg(posit)
    assert seg.last_msg == posit

    seg.add_msg(time_posit)
    assert seg.last_msg == time_posit

    # Make sure posit and posit time are being returned instead of just the last message
    seg = gpsdio_segment.core.Segment(1, ssvid=1)

    seg.add_msg(posit)
    seg.add_msg(non_posit)
    assert seg.last_msg == non_posit

    seg.add_msg(time_posit)
    seg.add_msg(non_posit)
    assert seg.last_msg == non_posit

    seg.add_msg(time_posit)
    seg.add_msg(non_posit)
    assert seg.last_msg == non_posit
