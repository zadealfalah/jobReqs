# Glue connection to RDS
resource "aws_glue_connection" "rds_connection" {
  name                 = "rds-connection"
  connection_properties = {
    USERNAME  = var.db_username
    PASSWORD  = var.db_password
    JDBC_CONNECTION_URL = "jdbc:mysql://${aws_db_instance.scrape-db.endpoint}:${aws_db_instance.scrape-db.port}/${aws_db_instance.scrape-db.db_name}"
  }

#   physical_connection_requirements {
#     availability_zone = aws_subnet.scraper-public-subnet-us-east-1a.availability_zone
#     security_group_id_list = [aws_security_group.e]
#   }
}


# Uploads the etl script to s3
# etag does a checksum comparing local to s3, redeploying if diffs exist
resource "aws_s3_object" "sql_job_script" {
  bucket = var.s3_bucket
  key = "sql_job_script.py"
  source = "${local.glue_src_path}sql_job_script.py"
  etag = filemd5("${local.glue_src_path}sql_job_script.py")
}


# Add cloudwatch log group for glue job
resource "aws_cloudwatch_log_group" "etl_cloudwatch_log_group" {
    name = "etl_cloudwatch_log_group"
    retention_in_days = 14
}



resource "aws_glue_job" "etl_job" {
  glue_version = "4.0" #optional
  max_retries = 0 #optional
  name = "sql_job_script" #required
  description = "test the deployment of an aws glue job to aws glue service with terraform" #description
  role_arn = aws_iam_role.glue_role.arn #required
  number_of_workers = 2 #optional, defaults to 5 if not set
  worker_type = "G.1X" #optional
  timeout = "15" #optional, in number of minutes

  command {
    name="glueetl" #optional, type of job we want to use e.g. gluestreaming, glueetl
    script_location = "s3://${var.s3_bucket}sql_job_script.py" #required, glue script location
  }

  connections = [ aws_glue_connection.rds_connection.name ]

  default_arguments = {
    "--continuous-log-logGroup"          = aws_cloudwatch_log_group.etl_cloudwatch_log_group.name
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-continuous-log-filter"     = "true"
    "--enable-metrics"                   = "true"
    "--class"                            = "GlueApp"
    "--enable-job-insights"              = "true"
    "--enable-auto-scaling"              = "false"
    "--enable-glue-datacatalog"          = "true"
    "--job-language"                     = "python"
    "--job-bookmark-option"              = "job-bookmark-disable"
  }
}

resource "aws_db_instance" "scrape-db" {
    allocated_storage    = 10
    db_name              = "scrapeindeed"
    engine               = "mysql"
    engine_version       = "8.0.35"
    instance_class       = "db.t3.micro"
    username             = var.db_username
    password             = var.db_password
    parameter_group_name = "default.mysql8.0"
    skip_final_snapshot  = true
    # db_subnet_group_name = aws_db_subnet_group.scrape-db-subnet-group.name
}
