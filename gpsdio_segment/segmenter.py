"""
Some ships using AIS are using the same ship identifiers, MMSI. This
means that it is not possible to directly distinguish points for one
ship from points from points for the other ship. In addition timing
noise in satellite clocks and bit noise in the received signals can
result in points or whole portions of tracks displaced in either
time or space.

To combat this we look at the projected position based on the reported
course and speed and consider whether it is plausible for the message
to correspond to one of the existing tracks or to start a new track.

The segmenter maintains a set of "open tracks". For each open tracks
it keeps the last point (latitude, longitude, course, speed and timestamp).
For each new point, it considers which of the open tracks to add
it to, or to create a new track, and also if it should close any
open tracks.

The details of how this is performed is best explained by examining
the logic in the function `matcher.compute_best`.
"""


from __future__ import division, print_function

import logging
from itertools import count

from gpsdio_segment.discrepancy import DiscrepancyCalculator
from gpsdio_segment.matcher import IS_NOISE, NO_MATCH, Matcher
from gpsdio_segment.msg_processor import (BAD_MESSAGE, INFO_ONLY_MESSAGE,
                                          POSITION_MESSAGE, MsgProcessor)
from gpsdio_segment.segment import (BadSegment, ClosedSegment,
                                    DiscardedSegment, InfoSegment, Segment)

logging.basicConfig()
logger = logging.getLogger(__file__)
logger.setLevel(logging.WARNING)

log = logger.info

inf = float("inf")


class Segmenter:

    """
    Group positional messages into related segments based on speed and distance.
    """

    def __init__(
        self,
        instream,
        ssvid=None,
        max_hours=Matcher.max_hours,
        max_open_segments=100,
        **kwargs,
    ):

        """
        Looks at a stream of messages and pull out segments of points that are
        related.  If an existing state is already known, instantiate from the
        `Segmenter()`

            >>> import gpsdio
            >>> from gpsdio_segment import Segmenter
            >>> with gpsdio.open(infile) as src, gpsdio.open(outfile) as dst:
            ...     for segment in Segmenter(src):
            ...        for msg in segment:
            ...            dst.write(msg)

        Parameters
        ----------
        instream : iter
            Stream of GPSd messages.
        ssvid : int, optional
            MMSI or other Source Specific ID to pull out of the stream and process.
            If not given, the first valid ssvid is used.  All messages with a
            different ssvid are thrown away.
        max_hours : float, optional
            Maximum number of hours to allow between points in a segment.
        max_open_segments : int, optional
            Maximum number of segments to keep open at one time. This is limited for performance
            reasons.

        """
        self.max_hours = max_hours
        self.max_open_segments = max_open_segments
        self._matcher = Matcher(max_hours=max_hours, **kwargs)
        self._msg_processor = MsgProcessor(self._matcher.very_slow, ssvid)

        # Exposed via properties
        self._instream = instream
        self._ssvid = ssvid

        # Internal objects
        self._segments = {}
        self._used_ids = set()

    def __repr__(self):
        return "<{cname}() max_knots={mspeed} max_hours={mhours} at {id_}>".format(
            cname=self.__class__.__name__,
            mspeed=self.max_knots,
            mhours=self.max_hours,
            id_=hash(self),
        )

    @classmethod
    def from_seg_states(cls, seg_states, instream, **kwargs):
        """
        Create a Segmenter and initialize its Segments from a stream of
        `SegmentStates()`, or a stream of dictionaries that can be converted
        via `SegmentState.fromdict()`.
        """
        s = cls(instream, **kwargs)
        for state in seg_states:
            if isinstance(state, dict):
                if state["closed"]:
                    continue
            else:
                if state.closed:
                    continue
            seg = Segment.from_state(state)
            s._segments[seg.id] = seg
            if seg.last_msg:
                ts = seg.last_msg["timestamp"]
                # TODO: clean up
                if s._msg_processor._prev_timestamp is None or ts > s._prev_timestamp:
                    s._prev_timestamp = ts
        return s

    @property
    def instream(self):
        return self._instream

    @property
    def ssvid(self):
        return self._ssvid

    @property
    def max_knots(self):
        # TODO: This is to preserve behavior during refactor, probably can be removed later
        return self._matcher.max_knots

    @property
    def cur_locations(self):
        # TODO: This is to preserve behavior during refactor, probably can be removed later
        return self._msg_processor.cur_locations

    @property
    def cur_msgids(self):
        # TODO: This is to preserve behavior during refactor, probably can be removed later
        return self._msg_processor.cur_msgids

    @property
    def cur_info(self):
        # TODO: This is to preserve behavior during refactor, probably can be removed later
        return self._msg_processor.info

    def _segment_unique_id(self, msg):
        """
        Generate a unique ID for a segment from a message, composed from its SSVID,
        timestamp, and an index to make it unique in the relatively rare case that
        two messages have the same timestamp.

        Returns
        -------
        str
        """
        for ndx in count(start=1):
            seg_id = f'{msg["ssvid"]}-{msg["timestamp"]:%Y-%m-%dT%H:%M:%S.%fZ}-{ndx}'
            if seg_id not in self._used_ids:
                self._used_ids.add(seg_id)
                return seg_id

    def _create_segment(self, msg, cls=Segment):
        """
        Create a new segment of desired class type and add `msg` to the segment.

        Returns
        -------
        Segment (specific type specified by `cls`)
        """
        id_ = self._segment_unique_id(msg)
        seg = cls(id_, self.ssvid)
        seg.add_msg(msg)
        return seg

    def _remove_excess_segments(self):
        """
        If there are too many segments open, close out the oldest ones.

        Yields
        -------
        ClosedSegment
        """
        while len(self._segments) >= self.max_open_segments:
            # Remove oldest segment
            segs = list(self._segments.items())
            segs.sort(
                key=lambda x: (
                    x[1].last_msg["timestamp"],
                    x[1].last_msg["msgid"],
                    x[1].last_msg["course"],
                    x[1].last_msg["speed"],
                )
            )
            stalest_seg_id, _ = segs[0]
            log("Removing stale segment {}".format(stalest_seg_id))
            yield from self._clean_segment(
                self._segments.pop(stalest_seg_id), ClosedSegment
            )

    def _add_segment(self, msg, why=None):
        """
        Remove any excess segments to save space and then add a new segment to _segments.

        Yields
        ------
        ClosedSegment
            Oldest segments closed out for memory reasons by `_removed_excess_segments()`.
        """
        if why is not None:
            log(f"adding new segment because {why}")
        yield from self._remove_excess_segments()
        seg = self._create_segment(msg)
        self._segments[seg.id] = seg

    def _clean_segment(self, segment, cls):
        """
        Clean a segment and output it as the specified `cls`. Cleaning involves
        adding necessary information to each message and dropping any messages
        that are designated to be dropped.

        Yields
        -------
        Segment
        DiscardedSegment
            Created for each messaged dropped from the clean segment
        """
        if segment.has_prev_state:
            new_segment = cls.from_state(segment.prev_state)
        else:
            new_segment = cls(segment.id, segment.ssvid)
        for msg in segment.msgs:
            self._msg_processor.add_info_to_msg(msg)
            msg.pop("metric", None)
            if msg.pop("drop", False):
                log(
                    (
                        "Dropping message from ssvid: {ssvid!r} timestamp: {timestamp!r}"
                    ).format(**msg)
                )
                yield self._create_segment(msg, cls=DiscardedSegment)
                continue
            else:
                new_segment.add_msg(msg)
        logging.debug("yielding cleaned segment with {len(new_segment.messages)}")
        yield new_segment

    def _process_bad_msg(self, msg):
        """
        Create a BadSegment from `msg`.

        Yields
        ------
        BadSegment
        """
        yield self._create_segment(msg, cls=BadSegment)
        logger.debug(
            (
                f"Rejected bad message from ssvid: {msg['ssvid']!r} lat: {msg['lat']!r}  lon: {msg['lon']!r} "
                f"timestamp: {msg['timestamp']!r} course: {msg['course']!r} speed: {msg['speed']!r}"
            )
        )

    def _process_info_only_msg(self, msg):
        """
        Create an InfoSegment from `msg`.

        Yields
        ------
        InfoSegment
        """
        yield self._create_segment(msg, cls=InfoSegment)
        logger.debug("Skipping info message from ssvid: %s", msg["ssvid"])

    def _process_ambiguous_match(self, msg, best_match):
        """
        Close each of the segments that matched the `msg` since the Matcher
        could not decide on a single segment. Add a new segment for the `msg`.

        Yields
        ------
        ClosedSegment
            For each matched segment
        Segment
            New segment started from `msg`
        """
        for match in best_match:
            yield from self._clean_segment(
                self._segments.pop(match["seg_id"]), cls=ClosedSegment
            )
        log(
            "adding new segment because of ambiguity with {} segments".format(
                len(best_match)
            )
        )
        yield from self._add_segment(msg)

    def _process_normal_match(self, msg, best_match):
        """
        Mark messages that need to be dropped and add `msg` to the
        matched segment.
        """
        id_ = best_match["seg_id"]
        for msg_to_drop in best_match["msgs_to_drop"]:
            msg_to_drop["drop"] = True
        msg["metric"] = best_match["metric"]
        self._segments[id_].add_msg(msg)
        return ()

    def _finalize_old_segments(self, msg):
        """
        Close any segments that have not had a position message in `self.max_hours`.

        Yields
        ------
        ClosedSegment
        """
        for segment in list(self._segments.values()):
            if (
                DiscrepancyCalculator.compute_msg_delta_hours(segment.last_msg, msg)
                > self.max_hours
            ):
                yield from self._clean_segment(
                    self._segments.pop(segment.id), cls=ClosedSegment
                )

    def _process_position_msg(self, msg):
        """
        If there are no segments currently, start a new segment with `msg`.
        Else, close out stale segments and then get the segment match for
        `msg` and handle appropriately.

        Yields
        ------
        ClosedSegment
            For all stale segments
        Segment
            Segments created during the matching process
        """
        if len(self._segments) == 0:
            yield from self._add_segment(msg, why="there are no current segments")
        else:
            yield from self._finalize_old_segments(msg)
            best_match = self._matcher.compute_best_match(msg, self._segments)

            if best_match is NO_MATCH:
                yield from self._add_segment(msg, why="no match")
            elif best_match is IS_NOISE:
                yield self._create_segment(msg, cls=BadSegment)
            elif isinstance(best_match, list):
                yield from self._process_ambiguous_match(msg, best_match)
            else:
                yield from self._process_normal_match(msg, best_match)

    def process(self):
        """
        Process each message based on its type. Bad messages and info only
        messages are immediately yielded as single message segments. Position
        messages are sent to be matched to segments and processed accordingly.
        When all messages have been processed, clean and yield all segments
        remaining in _segments.

        Yields
        ------
        Segment
        """
        for msg_type, msg in self._msg_processor(self.instream):

            if msg_type is BAD_MESSAGE:
                yield from self._process_bad_msg(msg)
            elif msg_type is INFO_ONLY_MESSAGE:
                yield from self._process_info_only_msg(msg)
            elif msg_type is POSITION_MESSAGE:
                yield from self._process_position_msg(msg)
            else:
                raise ValueError(f"unknown msg type {msg_type}")

        # Yield all pending segments now that processing is completed
        for series, segment in list(self._segments.items()):
            yield from self._clean_segment(self._segments.pop(segment.id), Segment)

    def __iter__(self):
        return self.process()
