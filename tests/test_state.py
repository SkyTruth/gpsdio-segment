import itertools
from datetime import datetime

from support import read_json

from gpsdio_segment.core import Segmentizer
from gpsdio_segment.segment import Segment, SegmentState


def test_SegmentState():
    s = SegmentState(
        id="ABC",
        ssvid="123456789",
        first_msg={"ssvid": 123456789, "timestamps": datetime.now()},
        last_msg={"ssvid": 123456789, "timestamps": datetime.now()},
        first_msg_of_day=None,
        last_msg_of_day=None,
        msg_count=1,
        noise=False,
        closed=False,
    )
    assert s._asdict() == SegmentState(**s._asdict())._asdict()


def test_Segment_state_save_load(msg_generator):
    id = 1
    ssvid = 123456789
    seg1 = Segment(id, ssvid)

    seg1.add_msg(msg_generator.next_msg())
    seg1.add_msg(msg_generator.next_posit_msg())
    seg1.add_msg(msg_generator.next_time_posit_msg())
    seg1.add_msg(msg_generator.next_time_posit_msg())
    state = seg1.state
    assert state.msg_count == 4
    seg1.add_msg(msg_generator.next_msg())
    state = seg1.state

    seg2 = Segment.from_state(state)
    assert seg2.id == id
    assert seg2.ssvid == ssvid
    assert len(seg2) == 0
    assert seg2.prev_state

    assert seg2.last_msg == seg1.last_msg

    msg = msg_generator.next_msg()
    seg2.add_msg(msg)
    assert seg2.last_msg == msg

    msg = msg_generator.next_posit_msg()
    seg2.add_msg(msg)
    assert seg2.last_msg == msg

    msg = msg_generator.next_time_posit_msg()
    seg2.add_msg(msg)
    assert seg2.last_msg == msg

    msg = msg_generator.next_msg()
    seg2.add_msg(msg)

    assert len(seg2) == 4
    state = seg2.state
    assert state.msg_count == 9


def test_Segmentizer_state_save_load(tmpdir):
    # outfile = str(
    #     tmpdir.mkdir("test_Segmentizer_state_save_load").join("segmented.json")
    # )

    with open("tests/data/416000000.json") as f:
        src = read_json(f)
        segmentizer = Segmentizer(src)
        segs = [seg for seg in segmentizer]
        # full_run_seg_states = [seg.state for seg in segs]
        # full_run_msg_count = sum(len(seg) for seg in segs)

    with open("tests/data/416000000.json") as f:
        src = read_json(f, add_msgid=True)
        n = 800
        segmentizer = Segmentizer(itertools.islice(src, n))
        segs = list(segmentizer)
        first_half_seg_states = [seg.state for seg in segs]
        assert n == sum([st.msg_count for st in first_half_seg_states])
        n2 = sum([st.msg_count for st in first_half_seg_states if not st.closed])

        segmentizer = Segmentizer.from_seg_states(first_half_seg_states, src)
        assert (
            sum([seg.prev_state.msg_count for seg in segmentizer._segments.values()])
            == n2
        )

        # second_half_seg_states = [seg.state for seg in segs]

        segmentizer = Segmentizer.from_seg_states(first_half_seg_states, src)
        assert (
            sum([seg.prev_state.msg_count for seg in segmentizer._segments.values()])
            == n2
        )


def test_Segmentizer_state_message_count_bug(msg_generator):
    seg = Segment(id=1, ssvid=123456789)
    seg.add_msg(msg_generator.next_time_posit_msg())
    state = seg.state
    assert state.msg_count == 1

    seg = Segment.from_state(state)
    seg.add_msg(msg_generator.next_msg())
    state = seg.state
    assert state.msg_count == 2
    state = seg.state
    assert state.msg_count == 2
