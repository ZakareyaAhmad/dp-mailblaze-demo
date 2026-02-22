resource "aws_s3_bucket" "terraform_bucket" {
  bucket = "dp-mailblaze-demo-dev-terraform"

  tags = {
    Project = "dp-mailblaze-demo"
    Env     = "dev"
    Managed = "terraform"
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_bucket" {
  bucket = aws_s3_bucket.terraform_bucket.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_bucket" {
  bucket = aws_s3_bucket.terraform_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}