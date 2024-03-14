import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import input_file_name, to_date, regexp_extract, explode
import logging


sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
logger = glueContext.get_logger()
spark = glueContext.spark_session
job = Job(glueContext)


logging.info("Creating spark dataframe from glue catalog")
df = glueContext.create_data_frame_from_catalog(database="gpt-bucket-database", 
                                                table_name="data",
                                                transformation_ctx="input_df"
                                                )




# DDL statements to create tables in RDS
ddl_statements = [
    """
    CREATE TABLE IF NOT EXISTS jobs (
        job_key VARCHAR(255) PRIMARY KEY,
        job_location VARCHAR(255),
        salary_min DECIMAL(10, 2),
        salary_max DECIMAL(10, 2),
        salary_type VARCHAR(50),
        salary_estimated_flag INT,
        company VARCHAR(255),
        job_title VARCHAR(255),
        job_date DATE,
        url VARCHAR(1000)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS keywords (
        id INT AUTO_INCREMENT PRIMARY KEY,
        job_key VARCHAR(255),
        keyword VARCHAR(255),
        FOREIGN KEY (job_key) REFERENCES jobs(job_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tech (
        id INT AUTO_INCREMENT PRIMARY KEY,
        job_key VARCHAR(255),
        technology VARCHAR(255),
        FOREIGN KEY (job_key) REFERENCES jobs(job_key)
    )
    """
]

# Execute DDL statements
for ddl_statement in ddl_statements:
    spark.sql(ddl_statement)




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

# e.g. jdbc url-  jdbc:mysql://endpoint:port/database.
# The following is an example JDBC URL: jdbc:redshift://examplecluster.abc123xyz789.us-west-2.redshift.amazonaws.com:5439/dev 

temp_db_endpoint_str = ""
temp_db_port_str = ""
temp_db_name_str = "scrapeindeed"

for table_name, data_frame in [("keywords", keywords_table), ("techs", techs_table), ("jobs", jobs_table)]:
    dynamic_frame = DynamicFrame.fromDF(data_frame, glueContext, f"{table_name}_dyf")

    datasink = glueContext.write_dynamic_frame_from_options(frame=dynamic_frame, connection_type="mysql", 
                                                            connection_options={
                                                                "url" : f"jdbc:mysql://{temp_db_endpoint_str}:{temp_db_port_str}/{temp_db_name_str}",
                                                                "user" : "",
                                                                "password" : "",
                                                                "dbtable" : table_name,
                                                                "redshiftTmpDir" : "s3://gpt-bucket-indeed/temp/"
                                                            }
                                                            )

# # Write the tables to rds (mysql)
# for table_name, data_frame in [("keywords", keywords_table), ("techs", techs_table), ("jobs", jobs_table)]:
#     dynamic_frame = DynamicFrame.fromDF(data_frame, glueContext, f"{table_name}_dyf")
#     glueContext.write_dynamic_frame.from_jdbc_conf(
#         frame=dynamic_frame,
#         catalog_connection="rds-connection",  # Specify the Glue connection name
#         connection_options={"dbtable": table_name, "database": "scrapeindeed"},
#         redshift_tmp_dir="s3://gpt-bucket-indeed/temp/"  # Temporary directory is not needed for RDS
#     )
