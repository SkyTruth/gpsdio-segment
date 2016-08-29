SELECT mmsi, lat, lon,  
  FORMAT_UTC_USEC(timestamp) as timestamp, 
  shipname,
  speed

FROM TABLE_DATE_RANGE([pipeline_classify_logistic_661b.], 
  TIMESTAMP('2015-11-19'), TIMESTAMP('2015-11-20'))

where mmsi in (224913000)
order by timestamp
LIMIT 100
