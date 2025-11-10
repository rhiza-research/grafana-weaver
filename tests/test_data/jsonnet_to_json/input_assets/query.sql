SELECT
  time,
  value
FROM metrics
WHERE time > NOW() - INTERVAL '1 hour'
