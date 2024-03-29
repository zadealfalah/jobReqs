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




##### Below is athena iam role
resource "aws_iam_user" "athena-user" {
  name = "athena-user"
  
}


resource "aws_iam_user_policy" "s3-athena-policy" {
  name = "s3-athena-policy"
  user = aws_iam_user.athena-user.name

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "SourceBucketReadOnlyAccess",
            "Effect": "Allow",
            "Action": [
                "s3:Get*",
                "s3:List*"
            ],
            "Resource": [
                "arn:aws:s3:::clean-gpt-bucket-indeed/data/*",
                "arn:aws:s3:::clean-gpt-bucket-indeed"
            ]
        }
    ]
})
}

resource "aws_iam_user_policy" "glue-athena-policy" {
  name = "glue-athena-policy"
  user = aws_iam_user.athena-user.name

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "GlueCatalog",
            "Effect": "Allow",
            "Action": [
                "glue:Get*"
            ],
            "Resource": [
                "arn:aws:glue:us-east-1:${var.aws_account_id}:catalog",
                "arn:aws:glue:us-east-1:${var.aws_account_id}:table/clean_gpt_catalog/*",
                "arn:aws:glue:us-east-1:${var.aws_account_id}:database/clean_gpt_catalog"
            ]
        }
    ]
})
}

resource "aws_iam_user_policy" "athena-resc-policy" {
  name = "athena-resc-policy"
  user = aws_iam_user.athena-user.name

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {   "Effect": "Allow",
            "Action": [
                "athena:ListEngineVersions",
                "athena:ListWorkGroups",
                "athena:ListDataCatalogs",
                "athena:ListDatabases",
                "athena:GetDatabase",
                "athena:ListTableMetadata",
                "athena:GetTableMetadata"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AthenaQueryExecution",
            "Effect": "Allow",
            "Action": [
                "athena:StartQueryExecution",
                "athena:StopQueryExecution",
                "athena:GetQuery*",
                "athena:GetWorkGroup"
            ],
            "Resource": "arn:aws:athena:us-east-1:${var.aws_account_id}:workgroup/primary"
        },
        {
            "Sid": "AthenaResultBucket",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject*",
                "s3:Get*",
                "s3:List*",
                "s3:AbortMultipartUpload",
                "s3:PutBucketPublicAccessBlock"
            ],
            "Resource": [
                "arn:aws:s3:::athena-bucket-indeed",
                "arn:aws:s3:::athena-bucket-indeed/*",
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::*"
            ]
        }
    ]
})
}

