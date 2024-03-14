# Glue connection to RDS
resource "aws_glue_connection" "rds_connection" {
  name                 = "rds-connection"
  connection_properties = {
    USERNAME  = var.db_username
    PASSWORD  = var.db_password
    JDBC_CONNECTION_URL = "jdbc:mysql://${aws_db_instance.scrape-db.endpoint}:${aws_db_instance.scrape-db.port}/${aws_db_instance.scrape-db.db_name}"
  }
}

# Uploads the etl script to s3
# etag does a checksum comparing local to s3, redeploying if diffs exist
resource "aws_s3_object" "sql_job_script" {
  bucket = var.s3_bucket
  key = "sql_job_script.py"
  source = "${local.glue_src_path}sql_job_script.py"
  etag = filemd5("${local.glue_src_path}sql_job_script.py")
}

resource "aws_glue_job" "etl_job" {
  glue_version = "4.0" #optional
  max_retries = 0 #optional
  name = "glueetl" #required
  description = "test the deployment of an aws glue job to aws glue service with terraform" #description
  role_arn = aws_iam_role.glue_service_role.arn #required
  number_of_workers = 2 #optional, defaults to 5 if not set
  worker_type = "G.1X" #optional
  timeout = "15" #optional, in number of minutes

  command {
    name="glueetl" #optional, type of job we want to use e.g. gluestreaming, glueetl
    script_location = "s3://${var.s3_bucket}/glue/scripts/sql_job_script.py" #required, glue script location
  }

  connections = [ aws_glue_connection.rds_connection.name ]

  default_arguments = {
    "--class"                   = "GlueApp"
    "--enable-job-insights"     = "true"
    "--enable-auto-scaling"     = "false"
    "--enable-glue-datacatalog" = "true"
    "--job-language"            = "python"
    "--job-bookmark-option"     = "job-bookmark-disable"
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
}