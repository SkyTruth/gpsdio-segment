import glob
import json
import os

import pytest
from support import read_json

from gpsdio_segment.core import Segmentizer

all_paths = glob.glob("tests/data/expected/*.json")
regr_paths = glob.glob("tests/data/expected/regr_*.json")
non_regr_paths = sorted(set(all_paths) - set(regr_paths))


def _test_expected(path):
    test_name = os.path.basename(path)
    with open(path) as f:
        src = list(read_json(f))
        expected_count = len([x for x in src if x["expected"] is not None])
        segmentizer = Segmentizer(src)
        cnt = 0
        for seg in segmentizer:
            for msg in seg:
                assert msg["expected"] == seg.id, test_name
                cnt += 1
        assert cnt == expected_count, test_name


@pytest.mark.parametrize("path", non_regr_paths)
def test_expected(path):
    _test_expected(path)


@pytest.mark.slow
@pytest.mark.parametrize("path", regr_paths)
def test_regression(path):
    _test_expected(path)


def dump_messages_as_json(src, path):
    """Dump segmenter messages as json

    Parameters
    ----------
    src: iterator yields dict
    path : src
    """
    if not src:
        return
    with open(path, "w") as f:
        for msg in src:
            msg = msg.copy()
            msg["timestamp"] = msg["timestamp"].isoformat()
            f.write(json.dumps(msg))
            f.write("\n")


# Stuff below here is all tools for creating more tests
# See CreateRegressionExamples notebook for example usage.


def iterate_over_tracks(tracks):
    """Iterate over individual tracks in a dataframe

    Tracks are returned in order of ssvid and are sorted
    by timestamp.

    Parameters
    ----------
    tracks : pd.Dataframe

    yields
    ------
    ssvid : str
    messages : list of dict
    """
    ssvid = None
    messages = None
    tracks = tracks.sort_values(by=["ssvid", "timestamp"], ignore_index=True)
    for x in tracks.itertuples():
        if x.ssvid != ssvid:
            if messages:
                yield ssvid, messages
            ssvid = x.ssvid
            messages = []
        else:
            messages.append(x._asdict())
    if messages:
        yield ssvid, messages


def add_expected(input_msgs):
    """Add expected seg_ids to messages

    The expected seg_id is added to the `expected` field. If the message
    gets dropped during segmentation, `expected` is set to None.

    N.B. Messages are modified in place

    Parameters
    ----------
    messages : list of dict
    """
    segmentizer = Segmentizer(input_msgs)
    for seg in segmentizer:
        for msg in seg:
            msg["expected"] = seg.id
    for msg in input_msgs:
        if "expected" not in msg:
            msg["expected"] = None
        # Replace `identities` and `destinations` field with JSON serializable
        # lists of dicts with item count added into the dict.
        if msg["identities"]:
            ids_serializable = []
            for id_key, count in msg["identities"].items():
                id_as_dict = id_key._asdict()
                id_as_dict["count"] = count
                ids_serializable.append(id_as_dict)
            msg["identities"] = ids_serializable
        if msg["destinations"]:
            dests_serializable = []
            for dest_key, count in msg["destinations"].items():
                dest_as_dict = dest_key._asdict()
                dest_as_dict["count"] = count
                dests_serializable.append(dest_as_dict)
            msg["destinations"] = dests_serializable
    return input_msgs
