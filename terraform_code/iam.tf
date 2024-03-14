data "aws_iam_policy_document" "glue_execution_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

# IAM policy for S3 access
data "aws_iam_policy_document" "s3_access_policy" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${var.s3_bucket}/*"]
  }
}

# IAM policy for RDS access
data "aws_iam_policy_document" "rds_access_policy" {
  statement {
    effect    = "Allow"
    actions   = ["rds-data:ExecuteStatement"]
    resources = ["arn:aws:rds:*:*:scrapeindeed/*"]  
  }
}

resource "aws_iam_policy" "glue_access_policy" {
  name   = "glue-access-policy"
  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["glue:*"],
        Resource = "*",
      },
    ],
  })
}

resource "aws_iam_role" "glue_service_role" {
  name               = "aws_glue_job_runner"
  assume_role_policy = data.aws_iam_policy_document.glue_execution_assume_role_policy.json
}

resource "aws_iam_policy" "s3_access_policy" {
  name   = "s3-access-policy"
  policy = data.aws_iam_policy_document.s3_access_policy.json
}

resource "aws_iam_policy" "rds_access_policy" {
  name   = "rds-access-policy"
  policy = data.aws_iam_policy_document.rds_access_policy.json
}

resource "aws_iam_role_policy_attachment" "glue_access_permissions" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = aws_iam_policy.glue_access_policy.arn
}

resource "aws_iam_role_policy_attachment" "s3_access_permissions" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = aws_iam_policy.s3_access_policy.arn
}

resource "aws_iam_role_policy_attachment" "rds_access_permissions" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = aws_iam_policy.rds_access_policy.arn
}
