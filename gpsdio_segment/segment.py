from __future__ import division, print_function

import logging
from collections import namedtuple

logging.basicConfig()
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


SegmentState = namedtuple(
    "SegmentState",
    [
        "id",
        "ssvid",
        "first_msg",
        "last_msg",
        "first_msg_of_day",
        "last_msg_of_day",
        "msg_count",
        "noise",
        "closed",
    ],
)


class Segment(object):

    """
    Contains all the messages that have been deemed by the `Segmenter()` to
    be continuous.
    """

    __slots__ = ["id", "ssvid", "msgs", "prev_state", "prev_segment", "msgs"]

    noise = False  # This isn't a 'real' segment, so it isn't written to a table
    closed = False  # No more segments should be written to this segment

    def __init__(self, id, ssvid):

        """
        Parameters
        ----------
        id : str or int
            Unique identifier for this segment.  If not globally unique must
            be unique within a given `Segmenter()` run.
        ssvid : int
            Source Specific ID (MMSI) contained within the segment.
        """
        self.id = id
        self.ssvid = ssvid
        self.prev_state = None
        self.prev_segment = None
        self.msgs = []

    @classmethod
    def from_state(cls, state):

        """
        Create a `Segment()` from a previously preserved segment state.  This
        allows continuity of segments across multiple independent processing
        runs.

        Returns
        -------
        Segment
        """
        if isinstance(state, dict):
            state = SegmentState(**state)
        seg = cls(state.id, state.ssvid)
        # Note that _noise and _closed come from the state
        seg.prev_state = state
        seg.prev_segment = Segment(state.id, state.ssvid)
        seg.prev_segment.add_msg(state.first_msg)
        seg.prev_segment.add_msg(state.last_msg)
        return seg

    def __repr__(self):
        return "<{cname}(id={id}, ssvid={ssvid}) with {msg_cnt} msgs at {hsh}>".format(
            cname=self.__class__.__name__,
            id=self.id,
            msg_cnt=len(self),
            ssvid=self.ssvid,
            hsh=hash(self),
        )

    def __iter__(self):
        return iter(self.msgs)

    def __len__(self):
        return len(self.msgs)

    @property
    def has_prev_state(self):
        return self.prev_segment is not None

    @property
    def state(self):

        """
        Capture the current state of the Segment.  Preserves the state of the
        latest messages for creating a new `Segment()` object in a future
        processing run.

        Returns
        -------
        SegmentState
        """
        return SegmentState(
            id=self.id,
            ssvid=self.ssvid,
            noise=self.noise,
            closed=self.closed,
            first_msg=self.first_msg,
            last_msg=self.last_msg,
            msg_count=self.msg_count,
            first_msg_of_day=self.first_msg_of_day,
            last_msg_of_day=self.last_msg_of_day,
        )

    @property
    def msg_count(self):
        n = len(self.msgs)
        if self.prev_state:
            n += self.prev_state.msg_count
        return n

    def get_all_reversed_msgs(self):
        source = self
        while source is not None:
            for msg in source.msgs[::-1]:
                if not msg.get("drop", False):
                    yield msg
            source = source.prev_segment

    @property
    def first_msg(self):
        if self.prev_state and self.prev_state.first_msg is not None:
            return self.prev_state.first_msg
        if self.msgs:
            return self.msgs[0]
        return None

    @property
    def last_msg(self):
        if self.msgs:
            return self.msgs[-1]
        if self.prev_state and self.prev_state.last_msg is not None:
            return self.prev_state.last_msg
        return None

    @property
    def first_msg_of_day(self):
        if self.msgs:
            return self.msgs[0]
        return None

    @property
    def last_msg_of_day(self):
        if self.msgs:
            return self.msgs[-1]
        return None

    def add_msg(self, msg):
        self.msgs.append(msg)


class ClosedSegment(Segment):
    """
    Segment that has timed out or closed because of ambiguity
    so we don't want to feed it back into Segmenter
    """

    closed = True


class NoiseSegment(ClosedSegment):
    """
    Segment that doesn't represent a real 'segment' for some reason.
    """

    noise = True


class BadSegment(NoiseSegment):
    """
    Sometimes points cannot be segmented for some reason, like if their
    location falls outside the world bounds, so rather than throw the point
    away we stick it into a `BadSegment()` so the user can filter with an
    instance check.
    """


class DiscardedSegment(NoiseSegment):
    """
    Points that are discarded during post processing of segments are emitted as
    Discarded segments.
    """


class InfoSegment(NoiseSegment):
    """
    Info messages that aren't matched to segments.
    """
