import math

inf = float("inf")


def is_null(v):
    return (v is None) or math.isnan(v)


def safe_course(msg):
    course = msg["course"]
    return 0 if is_null(course) else course


class DiscrepancyCalculator:
    """Base class that supplies discrepancy calculator"""

    # When vessels are traveling slowly, the can't always determine their
    # heading from GPS, so they return `360` (`unavailable`). Empirically,
    # almost all cases of this occur at or below 0.3 knots (the 0.05 is
    # account for floating point issues). When this occurs at `very_slow`
    # speeds we set the speed to zero when computing the discrepancy since
    # the heading is unknown. `unavailable` headings can also crop up at non-
    # slow speeds, presumably due to some issue with the AIS transponder.
    # These messages are discarded.
    very_slow = 0.35

    # Used in type 2 and 3 discrepancy calculations to increase the estimates
    # making it harder to match those ways because based on how vessels move,
    # it's less likely that a vessel didn't move or that it's somewhere between
    # the start and the end. It's much more likely that the vessel is somewhere
    # close to the estimated end point, so we want to prioritize that estimate.
    shape_factor = 4.0

    def _update(self, key, values):
        """Update existing instance value of `key` from value map if set

        Parameters
        ----------
        key : str
        values: dict
        """
        if key in values:
            setattr(self, key, values[key])
        elif not hasattr(self, key):
            raise ValueError('instance has no default value for "{}"'.format(key))

    @staticmethod
    def _compute_ts_delta_hours(ts1, ts2):
        """
        Compute difference between two timestamps, in hours.
        """
        return (ts2 - ts1).total_seconds() / 3600

    @staticmethod
    def compute_msg_delta_hours(msg1, msg2):
        """
        Compute difference between timestamps of two messages, in hours.
        """
        ts1 = msg1["timestamp"]
        ts2 = msg2["timestamp"]
        return DiscrepancyCalculator._compute_ts_delta_hours(ts1, ts2)

    @classmethod
    def _compute_expected_position(cls, msg, hours):
        """
        Compute where a vessel should be a certain amount of time
        (specified by `hours`) after a `msg`. Uses speed and course to
        calculate how far and in which direction a vessel has traveled
        and adds that to the previous known position.

        Returns
        -------
        (x, y)
        """
        epsilon = 1e-3
        x = msg["lon"]
        y = msg["lat"]
        speed = msg["speed"]
        course = msg["course"]
        if is_null(course):
            assert speed <= cls.very_slow, (course, speed)
            course = 0
            speed = 0
        # Speed is in knots, so `dist` is in nautical miles (nm)
        dist = speed * hours
        # Course is assumed to have `0` pointing north and positive
        # is clockwise as is reported by AIS. This in contrast with
        # the natural math based definition which has 0 pointing east
        # and positive being counter-clockwise, so we switch to that
        # here.
        course = math.radians(90.0 - course)
        deg_lat_per_nm = 1.0 / 60
        deg_lon_per_nm = deg_lat_per_nm / (math.cos(math.radians(y)) + epsilon)
        dx = math.cos(course) * dist * deg_lon_per_nm
        dy = math.sin(course) * dist * deg_lat_per_nm
        return x + dx, y + dy

    def compute_discrepancy(self, msg1, msg2, hours=None):
        """
        Compute the stats required to determine if two points are continuous.  Input
        messages must have a `lat`, `lon`, `course`, `speed` and `timestamp`,
        that are not `None` and `timestamp` must be an instance of `datetime.datetime()`.
        Three different metrics of discrepancies between points are calculated and
        the smallest one is returned. The discrepancies are:

        Type 1: the average of the distance between each pair
                of actual and expected positions

        Type 2: the distance difference if we assume the vessel
                stayed put at its initial point, penalized by
                multiplying by `shape_factor`

        Type 3: the distance perpendicular from the expected path
                to the known point calculated for `msg1` to `msg2`
                and vice versa and then averaged

        Returns
        -------
        float
        """
        if hours is None:
            hours = self.compute_msg_delta_hours(
                msg1,
                msg2,
            )
        assert hours >= 0

        x1 = msg1["lon"]
        y1 = msg1["lat"]
        assert x1 is not None and y1 is not None
        x2 = msg2.get("lon")
        y2 = msg2.get("lat")

        if x2 is None or y2 is None:
            discrepancy = None
        else:
            # Compute the expected position from both directions:
            # forward from `msg1` and backward from `msg2`.
            x2p, y2p = self._compute_expected_position(msg1, hours)
            x1p, y1p = self._compute_expected_position(msg2, -hours)

            def wrap(x):
                return (x + 180) % 360 - 180

            nm_per_deg_lat = 60.0
            y = 0.5 * (y1 + y2)
            nm_per_deg_lon = nm_per_deg_lat * math.cos(math.radians(y))

            # Type 1 Discrepancy
            discrepancy1 = 0.5 * (
                math.hypot(nm_per_deg_lon * wrap(x1p - x1), nm_per_deg_lat * (y1p - y1))
                + math.hypot(
                    nm_per_deg_lon * wrap(x2p - x2), nm_per_deg_lat * (y2p - y2)
                )
            )

            # Type 2 Discrepancy
            dist = math.hypot(
                nm_per_deg_lat * (y2 - y1), nm_per_deg_lon * wrap(x2 - x1)
            )
            discrepancy2 = dist * self.shape_factor

            # Type 3 Discrepancy
            rads21 = math.atan2(
                nm_per_deg_lat * (y2 - y1), nm_per_deg_lon * wrap(x2 - x1)
            )
            delta21 = math.radians(90 - safe_course(msg1)) - rads21
            tangential21 = math.cos(delta21) * dist
            if 0 < tangential21 <= msg1["speed"] * hours:
                normal21 = abs(math.sin(delta21)) * dist
            else:
                normal21 = inf
            delta12 = math.radians(90 - safe_course(msg2)) - rads21
            tangential12 = math.cos(delta12) * dist
            if 0 < tangential12 <= msg2["speed"] * hours:
                normal12 = abs(math.sin(delta12)) * dist
            else:
                normal12 = inf
            discrepancy3 = 0.5 * (normal12 + normal21) * self.shape_factor

            discrepancy = min(discrepancy1, discrepancy2, discrepancy3)

        return discrepancy
