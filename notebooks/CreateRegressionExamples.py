# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.13.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

import sys

sys.path.append("../tests")

import pandas as pd  # noqa: E402
import test_expected  # noqa: E402

# Download 10 days of Orbcomm data from each track in the baby pipe ssvid
# and process into the format
# that `test_extected` expects. This is used for regression testing the pipeline.

ssvids = pd.read_csv("../tests/data/baby_pipe_ssvids.csv")
ssvid_str = ",".join(f'"{x}"' for x in ssvids.ssvid)

query = f"""
SELECT *
FROM `pipe_ais_sources_v20201001.normalized_orbcomm_2021010*`
WHERE ssvid IN ({ssvid_str})
ORDER BY ssvid, timestamp, msgid
"""
tracks = pd.read_gbq(query, project_id="world-fishing-827")

for ssvid, track in test_expected.iterate_over_tracks(tracks):
    path = f"../tests/data/expected/regr_{ssvid}.json"
    test_expected.add_expected(track)
    test_expected.dump_messages_as_json(track, path)
