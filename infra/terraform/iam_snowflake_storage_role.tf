locals {
  raw_bucket_name = "dp-mailblaze-demo-dev-raw-3dfbc1"
}

resource "aws_iam_role" "snowflake_storage" {
  name = "dp-mailblaze-demo-dev-snowflake-storage"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSnowflakeAssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = var.snowflake_storage_aws_iam_user_arn
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.snowflake_storage_aws_external_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_policy" "snowflake_storage_s3_read" {
  name        = "dp-mailblaze-demo-dev-snowflake-storage-s3-read"
  description = "Allow Snowflake external stage to list/get objects from RAW bucket"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListBucket"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = "arn:aws:s3:::${local.raw_bucket_name}"
      },
      {
        Sid    = "ReadObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "arn:aws:s3:::${local.raw_bucket_name}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_read" {
  role       = aws_iam_role.snowflake_storage.name
  policy_arn = aws_iam_policy.snowflake_storage_s3_read.arn
}