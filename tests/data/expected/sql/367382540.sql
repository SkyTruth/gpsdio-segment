SELECT mmsi, lat, lon,  
  FORMAT_UTC_USEC(timestamp) as timestamp, 
  shipname,
  speed

FROM TABLE_DATE_RANGE([pipeline_740__classify.],
  TIMESTAMP('2015-01-01'), TIMESTAMP('2015-02-01'))

where mmsi in (367382540)
order by timestamp
LIMIT 100
