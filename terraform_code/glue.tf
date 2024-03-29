# # AWS Glue Catalog Database
# resource "aws_glue_catalog_database" "gpt_results_bucket" {
#   name = "gpt_results_bucket"
# }

# # AWS Glue Crawler
# resource "aws_glue_crawler" "crawl_gpt_bucket" {
#   database_name = aws_glue_catalog_database.gpt_results_bucket.name
#   name = "crawl_gpt_bucket"
#   role = aws_iam_role.glue_crawler_role.arn
#   schedule = "cron(1 1 * * ? *)"

#   s3_target {
#     path = "s3://${var.s3_gpt_data_bucket}"
#   }
# }

## Below uses the mapped terms from clean-gpt-bucket-indeed
# AWS Glue Catalog Database
resource "aws_glue_catalog_database" "clean_gpt_catalog" {
  name = "clean_gpt_catalog"
}

# AWS Glue Crawler
resource "aws_glue_crawler" "clean_gpt_crawler" {
  database_name = aws_glue_catalog_database.clean_gpt_catalog.name
  name = "clean_gpt_crawler"
  role = aws_iam_role.glue_crawler_role.arn
  schedule = "cron(1 1 * * ? *)"

  s3_target {
    path = "s3://${var.s3_clean_gpt_bucket}"
  }
}