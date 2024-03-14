from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import input_file_name, to_date, regexp_extract
import logging


def create_spark_context():
    sc = SparkContext()
    glueContext = GlueContext(sc)
    logger = glueContext.get_logger()
    spark = glueContext.spark_session
    job = Job(glueContext)
    return glueContext, spark

# input_dyf = glueContext.create_dynamic_frame.from_catalog(database='gpt-bucket-database', table_name='data', transformation_ctx='input_dyf')
def read_dataset_from_catalog(glueContext, database="gpt-bucket-database", table_name="data", transformation_ctx="input_dyf"):
    """
    Read dataset from Glue catalog
    :return dyf: DynamicFrame
    """
    logging.info("Reading dataset from Glue Catalog")
    dyf = glueContext.create_dynamic_frame.from_catalog(database=database, 
                                                        table_name=table_name,
                                                        transformation_ctx=transformation_ctx
                                                        )
    return dyf


def dynamicFrame_to_pyspark_dataframe(dyf):
    logging.info("Converting dynamic frame to pyspark dataframe")
    df = dyf.toDF()
    return df

def pyspark_dataframe_to_dynamicFrame(df, glue_ctx=glueContext, name="dyf"):
    logging.info("Converting pyspark dataframe to dynamic frame")
    dyf = DynamicFrame.fromDF(df, glue_ctx, name)
    return dyf

def add_filenames_to_dynamicFrame(dyf, glue_ctx=glueContext):
    """
    Adds the filenames with date information to the dynamic frames by transforming dyf-->df-->dyf
    :return dyf: DynamicFrame
    """
    logging.info("Adding filenames as columns")
    input_df = dyf.toDF()
    input_df = input_df.withColumn("filename", input_file_name())
    return_dyf = DynamicFrame.fromDF(input_df, glue_ctx, "dyf")
    return return_dyf
    
# Have as a function here to check keys from unnested, write unit tests for
def unnest_dynamic_frame(dyf, temp_path="s3://gpt-bucket-indeed/temp/", show_keys=True):
    """
    Unnest DynamicFrame via .relationalize
    :return dyf: DynamicFrame
    """
    logging.info("Relationalizing dynamicframe")
    unnested = dyf.relationalize('root', temp_path)
    if show_keys:
        logging.info(f"Unnested keys: {unnested.keys}")
    return unnested

def rename_dyf_field(dyf, oldName, newName):
    logging.info(f"Renaming dyf field from {oldName} to {newName}")
    return dyf.rename_field(
        oldName=oldName,
        newName=newName
    )

def rename_df_column(df, oldName, newName):
    logging.info(f"Renaming df field from {oldName} to {newName}")
    return df.withColumnRenamed(oldName, newName)


def drop_cols_from_df(df, cols_to_drop):
    logging.info(f"Dropping columns: {cols_to_drop}")
    return df.drop(*cols_to_drop)


def add_date_column_df(df, colname="date", search_str='r"\d{2}_\d{2}_\d{4}"', date_format="dd_MM_yyyy"):
    logging.info(f"Adding column: {colname}")
    return df.withColumn(colname, to_date(regexp_extract(df["filename"], search_str, 0), date_format))


def write_dataframe_to_s3(df, glueContext, path:str):
    """
    Write a dataframe as a dynamic frame to s3 bucket
    """
    logging.info("Writing dynamic frame to s3 bucket")
    # Convert pyspark dataframe to dyf
    dyf = pyspark_dataframe_to_dynamicFrame(df, glueContext, "dyf")
    # Write dyf to s3 bucket
    glueContext = GlueContext(SparkContext.getOrCreate())
    glueContext.write_dynamic_frame_from_options(frame=dyf, connection_type="s3",
                                                 connection_options={"path":path, 
                                                                     "partitionKeys": []},
                                                 format="parquet")

def main():
    """
    Main function of glue script
    """
    glueContext, spark = create_spark_context()
    dyf = read_dataset_from_catalog()
    dyf_filenames = add_filenames_to_dynamicFrame(dyf)
    unnested_dyf = unnest_dynamic_frame(dyf_filenames)
    
    # Get the dynamic frames for the roots we know we want
    # These are 'root', 'root_keyword', and 'root_choices.val.message.content'
    dyf_root = unnested_dyf.select('root')
    dyf_root_keyword_full = unnested_dyf.select('root_keyword')
    dyf_root_content = unnested_dyf.select('root_choices.val.message.content')
    
    # Rename the fields in the latter two dyfs
    dyf_root_tech = rename_dyf_field(dyf_root_content, "`choices.val.message.content.val`", "tech")
    dyf_root_keyword = rename_dyf_field(dyf_root_keyword_full, "`keyword.val`", "keyword_val")
    
    # Convert dyfs to dfs as we have a fixed schema and small memory usage, no big advantages to keeping as dyfs
    df_root = dynamicFrame_to_pyspark_dataframe(dyf_root)
    df_root_tech = dynamicFrame_to_pyspark_dataframe(dyf_root_tech)
    df_root_keyword = dynamicFrame_to_pyspark_dataframe(dyf_root_keyword)
    
    # Select only the relevant columns from root
    # Should just be 'job_key', 'keyword', 'choices', and 'filename'
    df_root_selected = df_root.select('job_key', 'keyword', 'choices', 'filename')
    
    # Join the root and the keyword
    # In root, 'keyword' is the keyword ID.  
    df_join_root_keyword = df_root_selected.join(
                                            df_root_keyword,
                                            df_root['keyword'] == df_root_keyword['id'])
    
    # Rename the 'index' column in df_join_root_keyword
    # Index identifies the position of the keyword in the original list of keyword searches
    df_join_root_keyword_renamed = rename_df_column(df_join_root_keyword,
                                                    "index",
                                                    "keyword_index")
    
    # Further join in the techs to the df_join_root_keyword_renamed dataframe
    df_join_rk_techs = df_join_root_keyword_renamed.join(
                                                    df_root_tech,
                                                    on='id')
    
    # Rename the 'index' column in df_join_rk_techs
    # Index identifies the position of the tech in the original list of techs
    df_join_rk_techs_renamed = rename_df_column(df_join_rk_techs, 
                                                "index",
                                                "tech_index")
    
    # Keyword and choices are both indexes from root which won't be needed
    cols_to_drop_default = ['keyword', 'choices']
    df_joined_dropped = drop_cols_from_df(df_join_rk_techs_renamed, cols_to_drop_default)
    
    # Get the date from the filename
    df_with_date = add_date_column_df(df_joined_dropped)
    
    # Drop the last of the unwanted columns
    cols_to_drop_final_default = ['id', 'filename', 'keyword_index', 'tech_index']
    df_final = drop_cols_from_df(df_with_date, cols_to_drop_final_default)
    
    # Show final output table
    df_final.show()
    
    #Write the final output as dyf to s3 as parquet file
    output_path = "s3://glue-bucket-indeed/processed"
    write_dataframe_to_s3(df_final, glueContext, output_path)
    
if __name__ =="__main__":
    main()