"""
Some debugging stuf.
"""

from datetime import datetime
from datetime import timedelta
import itertools as it
from collections import Counter

import pytest

import gpsdio
from gpsdio_segment.core import Segmentizer
from gpsdio_segment.core import BadSegment


def test_bad_segment():

    with gpsdio.open('tests/data/263576000.json') as src:
        # Run the whole thing - makes 2 segments, one of them is a BadSegment
        segmentizer = Segmentizer(src)
        segs = [seg for seg in segmentizer]
        assert Counter([seg.__class__.__name__ for seg in segs]) == {
                'DiscardedSegment': 113, 'Segment': 1, 'BadSegment': 1}
        assert {len(seg) for seg in segs} == {1, 834}

def test_bad_segment_daily():

    with gpsdio.open('tests/data/263576000.json') as src:
        # now run it one day at a time and store the segment states in between
        seg_types = {}
        seg_states = {}
        for day, msgs in it.groupby(src, key=lambda x: x['timestamp'].day):
            prev_states = seg_states.get(day - 1)
            if prev_states:
                segmentizer = Segmentizer.from_seg_states(prev_states, msgs)
            else:
                segmentizer = Segmentizer(msgs)

            segs = [seg for seg in segmentizer]
            seg_types[day] = Counter([seg.__class__.__name__ for seg in segs])


        # 1 bad segment the first day that does not get passed back in on the second day
        assert seg_types == {15: Counter({'DiscardedSegment': 59, 'Segment': 1, 'BadSegment': 1}),  
                             16: Counter({'DiscardedSegment': 54, 'Segment': 1})}

