import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import input_file_name, to_date, regexp_extract, explode
import logging
import boto3
import json

print("Imported")
args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
logger = glueContext.get_logger()
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)



logging.info("Creating spark dataframe from glue catalog")
df = glueContext.create_data_frame_from_catalog(database="gpt-bucket-database", 
                                                table_name="data",
                                                transformation_ctx="input_df"
                                                )




search_pattern = r'(\d{2}_\d{2}_\d{4})'
date_format="dd_MM_yyyy"

# Add the filenames to get the date information
df = df.withColumn("filename", input_file_name())
df = df.withColumn("job_date", to_date(regexp_extract(df["filename"], search_pattern, 0), date_format))

# Rename the 'location' column to 'job_location' for sql
df = df.withColumnRenamed('location', 'job_location')

# Get the keywords table
keywords_table = df.withColumn("keywords_exploded", explode("keyword"))\
    .select("job_key", "keywords_exploded")


# Get the techs table
techs_table = df.select("job_key", explode("choices").alias("choices"))\
    .select("job_key", "choices.*")\
    .select("job_key", explode("message.content").alias("tech"))


# Get the jobs table
jobs_table = df.select("job_key", "job_location", "from_age", "page", "position",
                       "salary_min", "salary_max", "salary_type", "salary_estimated_flag",
                       "job_description", "company", "job_title", "url", "split_jd", "job_date",
                    )

keywords_table.write.parquet("s3://glue-bucket-indeed/processed/keywords/testkw")
techs_table.write.parquet("s3://glue-bucket-indeed/processed/techs/testtech")
jobs_table.write.parquet("s3://glue-bucket-indeed/processed/jobs/testjob")


job.commit()

