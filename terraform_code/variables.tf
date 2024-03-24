variable "db_username" {
  description = "Database administrator username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database administrator password"
  type        = string
  sensitive   = true
}

variable "aws_access_key" {
    description = "AWS Terraform access key"
    type        = string
    sensitive   = true
}

variable "aws_secret_key" {
    description = "AWS Terraform secret access key"
    type        = string
    sensitive   = true
}

variable "aws_iam_user" {
    description = "AWS Terraform iam username"
    type        = string
    sensitive   = true
}

# To be updated
locals {
  glue_src_path = "${path.root}/glue/"
}

variable "s3_bucket" {
  type=string
  default = "glue-bucket-indeed"
}

variable "s3_gpt_data_bucket" {
    type=string
    default = "gpt-bucket-indeed/data"
}

variable "aws_account_id" {
  type=string
  sensitive = true
}

# # Below if I want to add tags
# variable "project" {
#   type=string
# }

variable "athena_user_aws_access_key" {
    type=string
    sensitive = true
}

variable "athena_user_aws_secret_key" {
    type=string
    sensitive = true
}