SELECT mmsi, lat, lon,  
  FORMAT_UTC_USEC(timestamp) as timestamp, 
  shipname,
  speed

FROM TABLE_DATE_RANGE([pipeline_740__classify.],
  TIMESTAMP('2015-11-05'), TIMESTAMP('2015-11-06'))

where mmsi in (412449638)
order by timestamp
LIMIT 100
