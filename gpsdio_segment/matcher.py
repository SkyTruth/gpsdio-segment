import logging
import math

from gpsdio_segment.discrepancy import DiscrepancyCalculator

logging.basicConfig()
logger = logging.getLogger(__file__)
logger.setLevel(logging.WARNING)

log = logger.info

NO_MATCH = object()
IS_NOISE = object()


POSITION_TYPES = {
    "AIS.1": {"AIS-A"},
    "AIS.2": {"AIS-A"},
    "AIS.3": {"AIS-A"},
    "AIS.18": {"AIS-B"},
    "AIS.19": {"AIS-B"},
    "AIS.27": {"AIS-A", "AIS-B"},
    "VMS": {"VMS"},
}


class Matcher(DiscrepancyCalculator):
    """
    Match messages to segments by comparing a message's position to
    the expected next position for each segment.

    Parameters
    ----------
        max_hours : float, optional
            Maximum number of hours to allow between points in a segment.
        penalty_hours : float, optional
            The effective hours is reduced at around this point.
        hours_exp: float, optional
            Exponent used when computing the penalty hours correction.
        buffer_hours: float, optional
            Time between points is padded by this amount when computing metrics.
        max_knots : int, optional
            Maximum speed allowed between points in nautical miles.
        lookback : int, optional
            Number of points to look backwards when matching segments.
        lookback_factor : float, optional:
            How much better a match to a previous point has to be in order to use lookback.
        short_seg_threshold : int, optional
            Segments shorter than this are penalized when computing metrics
        shape_factor : float, optional
            Controls how close we insist vessels to be along the path between their start
            and the their extrapolated destination if not near their destination. Large
            shape factor means very close.
        transponder_mismatch_weight : float, optional
            Weight to multiply messages by that have a different transponder type than the
            segment we want to match to. Should be between 0 and 1.
        penalty_speed : float, optional
            Speeds (relative to where we expect the boat to be) greater than this are strongly
            discouraged.
        min_type_27_hours : float, optional
            If a type 27 message occurs closer than this time to a non-type 27 message, it is
            dropped. This is because the low resolution type 27 messages can result in strange
            tracks, particularly when a vessel is in port.
    """

    # These default values are a result of generating segments
    # and assembling them into vessel tracks for a large number
    # of vessels.  There are enough knobs here that these are
    # likely still not optimal and more experimentation would likely
    # be helpful.
    max_hours = 24
    penalty_hours = 4
    hours_exp = 0.5
    buffer_hours = 0.25
    lookback = 5
    lookback_factor = 2
    max_knots = 25
    ambiguity_factor = 10.0
    short_seg_threshold = 10
    transponder_mismatch_weight = 0.1
    penalty_speed = 5.0
    min_type_27_hours = 1.0

    def __init__(self, **kwargs):

        for k in [
            "max_hours",
            "penalty_hours",
            "hours_exp",
            "buffer_hours",
            "max_knots",
            "lookback",
            "lookback_factor",
            "short_seg_threshold",
            "shape_factor",
            "transponder_mismatch_weight",
            "penalty_speed",
        ]:
            self._update(k, kwargs)
        self._discrepancy_alpha_0 = self.max_knots / self.penalty_speed

    @staticmethod
    def transponder_types(msg):
        return POSITION_TYPES.get(msg.get("type"), set())

    def compute_penalized_hours(self, hours):
        # Shorten the hours traveled relative to the length of travel
        # as boats tend to go straight for shorter distances, but at
        # longer distances, they may not go as straight or travel
        # the entire time
        return hours / (
            1 + (max(hours, 0) / self.penalty_hours) ** (1 - self.hours_exp)
        )

    def compute_metric(self, discrepancy, hours):
        padded_hours = math.hypot(hours, self.buffer_hours)
        max_allowed_discrepancy = padded_hours * self.max_knots
        if discrepancy > max_allowed_discrepancy:
            return 0
        alpha = self._discrepancy_alpha_0 * discrepancy / max_allowed_discrepancy
        return math.exp(-(alpha ** 2)) / padded_hours  # ** 2

    def _compute_segment_match(self, segment, msg):
        """
        Calculate metric for how likely `msg` is the next position
        for `segment`. Compare `msg` to mutliple messages at the
        end of `segment` (determined by `lookback`) in case this
        `msg` matches significantly better than previous messages
        added to the segment. If so, mark these messages to be dropped.

        Returns
        -------
        dict
        """
        match = {
            "seg_id": segment.id,
            "msgs_to_drop": [],
            "hours": None,
            "metric": None,
        }

        # Get the stats for the last `lookback` positional messages
        candidates = []
        n = len(segment)
        msgs_to_drop = []
        metric = 0
        transponder_types = set()
        for prev_msg in segment.get_all_reversed_msgs():
            n -= 1
            if prev_msg.get("drop"):
                continue
            transponder_types |= self.transponder_types(prev_msg)
            hours = self.compute_msg_delta_hours(prev_msg, msg)
            penalized_hours = self.compute_penalized_hours(hours)
            discrepancy = self.compute_discrepancy(prev_msg, msg, penalized_hours)
            candidates.append(
                (metric, msgs_to_drop[:], discrepancy, hours, penalized_hours)
            )
            if len(candidates) >= self.lookback or n < 0:
                # This allows looking back 1 message into the previous batch of messages
                break
            msgs_to_drop.append(prev_msg)
            metric = prev_msg.get("metric", 0)

        # Consider transponders matched if the transponder shows up in any of lookback items
        transponder_match = bool(transponder_types & self.transponder_types(msg))

        assert len(candidates) > 0

        best_metric_lb = 0
        for lookback, match_info in enumerate(candidates):
            (
                existing_metric,
                msgs_to_drop,
                discrepancy,
                hours,
                penalized_hours,
            ) = match_info
            assert hours >= 0
            if hours > self.max_hours:
                log("can't match due to max_hours")
                # Too long has passed, we can't match this segment
                break
            else:
                metric = self.compute_metric(discrepancy, hours)
                if metric > 0:
                    # Down weight cases where transceiver types don't match.
                    if not transponder_match:
                        metric *= self.transponder_mismatch_weight
                    # For lookback use the weight reduced by the lookback factor,
                    # But don't store this weight, use base metric instead.
                    metric_lb = metric / max(1, lookback * self.lookback_factor)
                    # Scale the existing metric using the lookback factor so that we only
                    # matches to points further in the past if they are noticeably better
                    if metric_lb <= existing_metric:
                        log(
                            "can't make metric worse: %s vs %s (%s) at lb %s",
                            metric_lb,
                            existing_metric,
                            metric,
                            lookback,
                        )
                        # Don't make existing segment worse
                        continue
                    if metric_lb > best_metric_lb:
                        log("updating metric %s (%s)", metric_lb, metric)
                        best_metric_lb = metric_lb
                        match["metric"] = metric
                        match["hours"] = hours
                        match["msgs_to_drop"] = msgs_to_drop
                else:
                    log("can't match due to discrepancy: {discrepancy} / {hours}")

        return match

    def compute_best_match(self, msg, segments):
        """
        Determine which segment(s) is the best match for a given message.

        Return
        ------
        object
            One of the following: NO_MATCH, IS_NOISE, list of dict, or dict
        """

        segs = list(segments.values())
        best_match = NO_MATCH

        # get match metrics for all candidate segments
        raw_matches = [self._compute_segment_match(seg, msg) for seg in segs]
        # If metric is none, then the segment is not a match candidate
        matches = [x for x in raw_matches if x["metric"] is not None]

        if len(matches) == 1:
            # This is the most common case, so make it optimal
            # and avoid all the messing around with lists in the num_segs > 1 case
            [best_match] = matches
        elif len(matches) > 1:
            # Down-weight (decrease metric) for short segments
            valid_segs = [s for s, m in zip(segs, raw_matches) if m is not None]
            alphas = [s.msg_count / self.short_seg_threshold for s in valid_segs]
            metric_match_pairs = [
                (m["metric"] * a / math.sqrt(1 + a ** 2), m)
                for (m, a) in zip(matches, alphas)
            ]
            metric_match_pairs.sort(key=lambda x: x[0], reverse=True)
            # Check if best match is close enough to an existing match to be ambiguous.
            best_metric, best_match = metric_match_pairs[0]
            close_matches = [best_match]
            for metric, match in metric_match_pairs[1:]:
                if metric * self.ambiguity_factor >= best_metric:
                    close_matches.append(match)
            if len(close_matches) > 1:
                log("Ambiguous messages for id {}".format(msg["ssvid"]))
                best_match = close_matches

        if best_match is not NO_MATCH:
            hours = (
                min([x["hours"] for x in best_match])
                if isinstance(best_match, list)
                else best_match["hours"]
            )
            if msg.get("type") == "AIS.27" and hours < self.min_type_27_hours:
                # Type 27 messages have low resolution, so only include them where there likely to
                # not mess up the tracks
                return IS_NOISE

        return best_match
