"""
Tools for segmenting positional AIS messages into continuous tracks.

Includes a CLI plugin for `gpsdio` to run the algorithm.
"""


from gpsdio_segment.core import Segmentizer  # noqa: F401
from gpsdio_segment.segment import BadSegment, Segment  # noqa: F401

__version__ = "3.0.0"

__author__ = "Paul Woods"
__email__ = "paul@skytruth.org"
__source__ = "https://github.com/SkyTruth/gpsdio-segment"
__license__ = """
Copyright 2015-2020 SkyTruth
Authors:

Kevin Wurster <kevin@skytruth.org>
Paul Woods <paul@skytruth.org>
Tim Hochberg <tim@globalfishingwatch.org>
Andres Arana <andres@globalfishingwatch.org>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
