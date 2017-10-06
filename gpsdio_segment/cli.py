"""
Commandline interface for gpsdio-segment
"""


import logging

import click
import gpsdio
import gpsdio.drivers

import gpsdio_segment
from gpsdio_segment.core import Segmentizer
from gpsdio_segment.core import DEFAULT_MAX_SPEED
from gpsdio_segment.core import DEFAULT_MAX_HOURS
from gpsdio_segment.core import DEFAULT_NOISE_DIST
from gpsdio_segment.core import MAX_SPEED_MULTIPLIER
from gpsdio_segment.core import MAX_SPEED_EXPONENT


@click.command()
@click.version_option(version=gpsdio_segment.__version__)
@click.argument('infile', required=True)
@click.argument('outfile', required=True)
@click.option(
    '--mmsi', type=click.INT,
    help="Only segment this MMSI.  If not given the first MMSI found will be used."
)
@click.option(
    '--max-hours', type=click.FLOAT, default=DEFAULT_MAX_HOURS,
    help="Points with a time delta larger than N hours are forced to be discontinuous. "
         "(default: {})".format(DEFAULT_MAX_HOURS)
)
@click.option(
    '--max-speed', type=click.FLOAT, default=DEFAULT_MAX_SPEED,
    help="Units are knots.  Points with a speed above this value are always considered "
         "discontinuous. (default: {})".format(DEFAULT_MAX_SPEED)
)
@click.option(
    '--noise-dist', type=click.FLOAT, default=DEFAULT_NOISE_DIST,
    help="The distance within which, if another segment is "
         "(default: {})".format(DEFAULT_NOISE_DIST)
)
@click.option(
    '--max-speed-multiplier', type=click.FLOAT, default=MAX_SPEED_MULTIPLIER,
    help="speed cutoff equation parameter"
         "(default: {})".format(MAX_SPEED_MULTIPLIER)
)
@click.option(
    '--max-speed-exponent', type=click.FLOAT, default=MAX_SPEED_EXPONENT,
    help="speed cutoff equation parameter"
         "(default: {})".format(MAX_SPEED_EXPONENT)
)
@click.option(
    '--segment-field', default='segment',
    help="Add the segment ID to this field when writing messages. (default: segment)"
)
@click.pass_context
def segment(ctx, infile, outfile, mmsi, max_hours, max_speed, noise_dist,
 segment_field, max_speed_multiplier, max_speed_exponent):

    """
    Group AIS data into continuous segments.
    """

    logger = logging.getLogger(__file__)

    with gpsdio.open(infile, driver=ctx.obj.get('i_drv'),
                     compression=ctx.obj.get('i_cmp')) as src, \
            gpsdio.open(outfile, 'w',
                        driver=ctx.obj.get('o_drv'), compression=ctx.obj.get('o_cmp')) as dst:

        logger.debug("Beginning to segment")
        for t_idx, seg in enumerate(Segmentizer(
                src, mmsi=mmsi, max_hours=max_hours,
                max_speed=max_speed, noise_dist=noise_dist,
                 max_speed_multiplier=max_speed_multiplier,
                 max_speed_exponent=max_speed_exponent)):

            logger.debug("Writing segment %s with %s messages and %s points",
                         seg.id, len(seg), len(seg.coords))
            for msg in seg:
                msg[segment_field] = seg.id
                dst.write(msg)
