SELECT mmsi, lat, lon,  
  FORMAT_UTC_USEC(timestamp) as timestamp, 
  shipname,
  speed

FROM TABLE_DATE_RANGE([pipeline_740__classify.],
  TIMESTAMP('2015-04-17'), TIMESTAMP('2015-04-18'))

where mmsi in (412349342)
order by timestamp
LIMIT 100
