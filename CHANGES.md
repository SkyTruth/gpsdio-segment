# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## 0.20.2 - 2020-10-13

### Fixes

* [PIPELINE-144](https://globalfishingwatch.atlassian.net/browse/PIPELINE-144):
  Fixes the identity assignment logic so that identity messages appearing after
  a batch of positional messages are not discarded.

## 0.20.1 - 2020-10-06

### Changes

* [PIPELINE-139](https://globalfishingwatch.atlassian.net/browse/PIPELINE-139):
  Removes the receiver from the identity cache because that field is completely
  broken.

## 0.20 - 2020-04-07

### Added

* [GlobalFishingWatch/gfw-eng-tasks#47](https://github.com/GlobalFishingWatch/gfw-eng-tasks/issues/47): Adds
    guard code over `course` field when has None value when normalize message.

## 0.19

### Changes

* Change to a metric based primarily on "discrepancy" which is how far the vessel is from where we expect it to be based on its course and speed.
* What we mean by expect is informed by the experiments in extracting probability clouds for AIS matching.
* Many heuristics are applied based on extensive experimentation, but more experimentation would still be helpful.

## 0.18

### Changes

* [GlobalFishingWatch/GFW-Tasks#1015](https://github.com/GlobalFishingWatch/GFW-Tasks/issues/1015)
  * Remove checks for name/callsign when assigning segments.
  * Never check for transceiver type.
  * Add type 3 messages to class A message types.

## 0.17

### Changes
* Fix version of pyproj to avoid going to 2.X

## 0.16

### ADDED
* [#61](https://github.com/SkyTruth/gpsdio-segment/issues/61)
  Prefer segments with matching shipname and/or callsign
* [#63](https://github.com/SkyTruth/gpsdio-segment/issues/63)
  Treat a duplicate timestamp that is within noise distance from an existing segment as noise
* [#66](https://github.com/SkyTruth/gpsdio-segment/issues/66)
  When no shipname or callsign matches, prefer the segment with the most recent position

## 0.12
* [#60](https://github.com/SkyTruth/gpsdio-segment/pull/60) 
  Prefer segments with the same message type


## 0.11 - (2017-12-31)

* ['#54'](https://github.com/SkyTruth/gpsdio-segment/pull/54)
  Ignore noise segments in Segmentizer.from_seg_states()

* ['#56'](https://github.com/SkyTruth/gpsdio-segment/pull/56)
  Performance improvement for the special case where all messages added to a segment are 
  non-positional (have no lat/lon as is the case with type 5 AIS messages)

## 0.10 - (2017-12-22)

* ['#50'](https://github.com/SkyTruth/gpsdio-segment/pull/50)
  Emit noise messages in a new segment class `NoiseSegment` that works like 
  `BadSegment`

* ['#49'](https://github.com/SkyTruth/gpsdio-segment/pull/49)
  New option `collect_match_stats` for Segmentizer that captures all the stats used to 
  determine which segment a message is added to.  The stats are added to the message in 
  a field called `segment_matches`

  
## 0.9 - (2017-10-18)

- New parameters that reduce the allowable speed at distance and handle noise better #42


## 0.8 - (2017-08-22)

- Documentation and reorganization


## 0.7 - (2017-01-26)

- Bugfix for no reported speed.


## 0.6 - (2016-08-30)

- Improved segmenting algorithm to handle high speed better .  #32, #34


## 0.5 - (2016-06-10)

- Better handling bad locations to prevent subsequent positions from being added to `BadSegment()`.  #29


## 0.4 - (2016-05-23)

- Handle an edge case where a non-posit is the first message encountered after clearing out _all_ segments.  #24


## 0.3 - (2016-05-17)

- Better handling for out-of-bounds locations.  #17
- Shush logging.  #19


## 0.2 - (2015-10-06)

- Added states for Segmentizer and Segments.  #13


## 0.1 - (2015-06-24)

- Initial release.
