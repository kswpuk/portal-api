locals {
  domain = "${var.prefix}.${var.domain}"
}

# S3 Hosting

resource "aws_s3_bucket" "hosting" {
  bucket = local.domain
}

resource "aws_s3_bucket_cors_configuration" "hosting" {
  bucket = aws_s3_bucket.hosting.bucket

  cors_rule {
    allowed_headers = ["Authorization", "Content-Length"]
    allowed_methods = ["GET", "POST"]
    allowed_origins = ["https://${local.domain}"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_website_configuration" "hosting" {
  bucket = aws_s3_bucket.hosting.bucket

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "hosting" {
  bucket = aws_s3_bucket.hosting.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "hosting" {
  bucket = aws_s3_bucket.hosting.id
  policy = data.aws_iam_policy_document.hosting.json

  depends_on = [aws_s3_bucket_public_access_block.hosting]
}

# resource "aws_s3_bucket_acl" "hosting" {
#   bucket = aws_s3_bucket.hosting.id
#   acl    = "public-read"
# }

data "aws_iam_policy_document" "hosting" {
  statement {
    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = [
      "s3:GetObject",
    ]

    resources = [
      "${aws_s3_bucket.hosting.arn}/*",
    ]
  }
}

# SSL Certificate

resource "aws_acm_certificate" "hosting" {
  provider = aws.acm_provider

  domain_name       = local.domain
  validation_method = "DNS"
}

resource "aws_acm_certificate_validation" "hosting" {
  provider = aws.acm_provider

  certificate_arn         = aws_acm_certificate.hosting.arn
  validation_record_fqdns = [for record in aws_route53_record.validation : record.fqdn]
}

# Cloudfront
resource "aws_cloudfront_distribution" "hosting" {
  depends_on = [aws_s3_bucket.hosting]

  origin {
    domain_name = aws_s3_bucket.hosting.website_endpoint
    origin_id   = "S3-${local.domain}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1", "TLSv1.1", "TLSv1.2"]
    }
  }

  aliases = [local.domain]

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  custom_error_response {
    error_caching_min_ttl = 0
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${local.domain}"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 31536000
    default_ttl            = 31536000
    max_ttl                = 31536000
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.hosting.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.1_2016"
  }
}

# Route 53
data "aws_route53_zone" "domain" {
  name         = var.domain
  private_zone = false
}

resource "aws_route53_record" "portal" {
  zone_id = data.aws_route53_zone.domain.zone_id
  name    = local.domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.hosting.domain_name
    zone_id                = aws_cloudfront_distribution.hosting.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "validation" {
  for_each = {
    for dvo in aws_acm_certificate.hosting.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.domain.zone_id
}
