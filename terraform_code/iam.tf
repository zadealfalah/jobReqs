# IAM Role for Glue crawler Script
resource "aws_iam_role" "glue_crawler_role" {
  name               = "glue_crawler_role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
}

# Attach complete s3 access policy to glue role
resource "aws_iam_policy_attachment" "glue_s3_attachment" {
  name       = "glue_s3_attachment"
  roles      = [aws_iam_role.glue_crawler_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Create cloudwatch logs policy
resource "aws_iam_policy" "cloudwatch_logs_policy" {
  name        = "glue_crawler_cloudwatch_logs_policy"
  description = "Policy for Glue crawler to write logs to CloudWatch Logs"

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "*"
      }
    ]
  })
}
# Attach cloudwatch logs policy
resource "aws_iam_role_policy_attachment" "glue_crawler_cloudwatch_logs_access" {
  role       = aws_iam_role.glue_crawler_role.name
  policy_arn = aws_iam_policy.cloudwatch_logs_policy.arn
}

# Attach glue service role policy
resource "aws_iam_role_policy_attachment" "glue_crawler_policy_attachment" {
  role       = aws_iam_role.glue_crawler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}
