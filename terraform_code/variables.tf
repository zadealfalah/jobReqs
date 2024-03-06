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