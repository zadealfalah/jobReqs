CREATE OR REPLACE VIEW jobs_view AS
WITH 
    t1 AS (
        SELECT
            job_key, 
            tech,
            date_parse(cast(year * 10000 + month * 100 + day as varchar(255)), '%Y%m%d') AS job_date
        FROM 
        data
        CROSS JOIN UNNEST(cleaned_techs) AS t(tech)
        ),
    t2 AS (
        SELECT 
            job_key,
            kw
        FROM keywords_raw
        CROSS JOIN UNNEST(keyword) as t(kw)
        )
    
SELECT 
    t1.job_key, 
    t1.tech, 
    t1.job_date,
    t2.kw

FROM t1
JOIN t2
    ON t1.job_key = t2.job_key