#!/bin/bash

for f in  sql/* ; do
  MMSI=$(basename $f .sql)

  cat $f \
    | bq --project=world-fishing-827 -q query --format=json | \
    jq -c 'def tonumberq: tonumber? // .; .[] | {mmsi: .mmsi | tonumberq, lat: .lat | tonumberq, lon: .lon | tonumberq, timestamp: .timestamp, speed: .speed | tonumberq}' \
    | gpsdio -q --i-drv NewlineJSON --o-drv NewlineJSON segment --segment-field expected - - \
    | jq --slurp -c 'sort_by(.timestamp)[]' \
    > ./${MMSI}.json
done


