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

from gpsdio_segment.segmenter import (  # noqa: F401
    BAD_MESSAGE,
    INFO_ONLY_MESSAGE,
    IS_NOISE,
    NO_MATCH,
    POSITION_MESSAGE,
    BadSegment,
    ClosedSegment,
    DiscardedSegment,
    DiscrepancyCalculator,
    InfoSegment,
    Matcher,
    MsgProcessor,
    Segment,
    Segmenter,
)


class Segmentizer(Segmenter):
    """
    Temporary pass-through class for backwards compatibility with the old
    class name `Segmentizer`. Moving forward, this class is now called
    `Segmenter` and is held in `segmenter.py`.

    TODO: Remove this once `pipe-segment` repo has been updated to use
    the `Segmenter` class, formerly `Segmentizer`, now held in `segmenter.py`.
    """

    pass
