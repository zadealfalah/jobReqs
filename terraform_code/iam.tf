# Set up database security groups

# Security group to allow glue access to mysql
resource "aws_security_group" "glue_security_group" {
  vpc_id = aws_vpc.glue_vpc.id
}

resource "aws_vpc_security_group_ingress_rule" "allow_tls_ipv4" {
  security_group_id = aws_security_group.glue_security_group.id
  from_port = 3306
  to_port = 3306
  ip_protocol = "tcp"
  referenced_security_group_id = aws_security_group.glue_security_group.id

}

resource "aws_vpc_security_group_egress_rule" "allow_ipv4_traffic" {
  security_group_id = aws_security_group.glue_security_group.id
  ip_protocol = "-1" # all ports
  referenced_security_group_id = aws_security_group.glue_security_group.id

}

resource "aws_vpc_security_group_ingress_rule" "glue_self_rule" {
  security_group_id = aws_security_group.glue_security_group.id
  ip_protocol = "-1"
  from_port = 0
  to_port = 65535
  referenced_security_group_id = aws_security_group.glue_security_group.id
}






# IAM Role for Glue Script
resource "aws_iam_role" "glue_role" {
  name               = "glue_role"
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

# IAM Policy for Glue Role to access S3
resource "aws_iam_policy" "glue_s3_policy" {
  name        = "glue_s3_policy"
  description = "IAM policy for Glue to access S3"

  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject"
        ],
        Resource = "arn:aws:s3:::your_bucket/*" # Replace `your_bucket` with your actual S3 bucket name
      }
    ]
  })
}

# Attach S3 policy to Glue role
resource "aws_iam_policy_attachment" "glue_s3_attachment" {
  name       = "glue_s3_attachment"
  roles      = [aws_iam_role.glue_role.name]
  policy_arn = aws_iam_policy.glue_s3_policy.arn
}

# IAM Policy for Glue Role to access RDS
resource "aws_iam_policy" "glue_rds_policy" {
  name        = "glue_rds_policy"
  description = "IAM policy for Glue to access RDS"

  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "rds-db:connect"
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach RDS policy to Glue role
resource "aws_iam_policy_attachment" "glue_rds_attachment" {
  name       = "glue_rds_attachment"
  roles      = [aws_iam_role.glue_role.name]
  policy_arn = aws_iam_policy.glue_rds_policy.arn
}