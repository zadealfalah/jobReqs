
# etag does a checksum comparing local to s3, redeploying if diffs exist
resource "aws_s3_object" "test_deploy_script_s3" {
  bucket = var.s3_bucket
  key = "glue/scripts/TestDeployScript.py"
  source = "${local.glue_src_path}TestDeployScript.py"
  etag = filemd5("${local.glue_src_path}TestDeployScript.py")
}

resource "aws_glue_job" "test_deploy_script" {
  glue_version = "4.0" #optional
  max_retries = 0 #optional
  name = "TestDeployScript" #required
  description = "test the deployment of an aws glue job to aws glue service with terraform" #description
  role_arn = aws_iam_role.glue_service_role.arn #required
  number_of_workers = 2 #optional, defaults to 5 if not set
  worker_type = "G.1X" #optional
  timeout = "60" #optional, in number of minutes
  execution_class = "FLEX" #optional
  tags = {
    project = var.project #optional
  }
  command {
    name="glueetl" #optional, type of job we want to use e.g. gluestreaming, glueetl
    script_location = "s3://${var.s3_bucket}/glue/scripts/TestDeployScript.py" #required, glue script location
  }
  default_arguments = {
    "--class"                   = "GlueApp"
    "--enable-job-insights"     = "true"
    "--enable-auto-scaling"     = "false"
    "--enable-glue-datacatalog" = "true"
    "--job-language"            = "python"
    "--job-bookmark-option"     = "job-bookmark-disable"
  }
}