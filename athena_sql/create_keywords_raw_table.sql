CREATE EXTERNAL TABLE IF NOT EXISTS keywords_raw ( job_key string, keyword ARRAY<string> )
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://clean-gpt-bucket-indeed/data/'