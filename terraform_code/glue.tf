# AWS Glue Catalog Database
resource "aws_glue_catalog_database" "gpt_results_bucket" {
  name = "gpt_results_bucket"
}

# AWS Glue Crawler
resource "aws_glue_crawler" "crawl_gpt_bucket" {
  database_name = aws_glue_catalog_database.gpt_results_bucket.name
  name = "crawl_gpt_bucket"
  role = aws_iam_role.glue_crawler_role.arn
  schedule = "cron(1 1 * * ? *)"

  s3_target {
    path = "s3://${var.s3_gpt_data_bucket}"
  }
}
