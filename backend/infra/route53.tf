# SBH Route 53 and ACM - Phase 2 Cloud Deployment

# =============================================================================
# ACM CERTIFICATE
# =============================================================================

resource "aws_acm_certificate" "sbh_cert" {
  domain_name       = "sbh.umbervale.com"
  validation_method = "DNS"

  subject_alternative_names = [
    "*.sbh.umbervale.com"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name        = "${var.project_name}-cert-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# =============================================================================
# ROUTE 53 ZONE (assuming umbervale.com zone exists)
# =============================================================================

# Commented out until Route 53 hosted zone is created in AWS
# data "aws_route53_zone" "umbervale" {
#   name         = "umbervale.com."
#   private_zone = false
# }

# =============================================================================
# ACM CERTIFICATE VALIDATION (Commented out until Route 53 zone exists)
# =============================================================================

# resource "aws_route53_record" "sbh_cert_validation" {
#   for_each = {
#     for dvo in aws_acm_certificate.sbh_cert.domain_validation_options : dvo.domain_name => {
#       name   = dvo.resource_record_name
#       record = dvo.resource_record_value
#       type   = dvo.resource_record_type
#     }
#   }

#   allow_overwrite = true
#   name            = each.value.name
#   records         = [each.value.record]
#   ttl             = 60
#   type            = each.value.type
#   zone_id         = data.aws_route53_zone.umbervale.zone_id
# }

# resource "aws_acm_certificate_validation" "sbh_cert_validation" {
#   certificate_arn         = aws_acm_certificate.sbh_cert.arn
#   validation_record_fqdns = [for record in aws_route53_record.sbh_cert_validation : record.fqdn]
# }

# =============================================================================
# ROUTE 53 RECORDS (Commented out until Route 53 zone exists)
# =============================================================================

# resource "aws_route53_record" "sbh_domain" {
#   zone_id = data.aws_route53_zone.umbervale.zone_id
#   name    = "sbh.umbervale.com"
#   type    = "A"

#   alias {
#     name                   = aws_lb.sbh_alb.dns_name
#     zone_id                = aws_lb.sbh_alb.zone_id
#     evaluate_target_health = true
#   }
# }

# =============================================================================
# HTTPS LISTENER (Commented out until certificate validation is set up)
# =============================================================================

# resource "aws_lb_listener" "sbh_https_listener" {
#   load_balancer_arn = aws_lb.sbh_alb.arn
#   port              = "443"
#   protocol          = "HTTPS"
#   ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
#   certificate_arn   = aws_acm_certificate_validation.sbh_cert_validation.certificate_arn

#   default_action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.sbh_tg.arn
#   }

#   tags = {
#     Name        = "${var.project_name}-https-listener-${var.environment}"
#     Environment = var.environment
#     Project     = var.project_name
#   }
# }

# =============================================================================
# HTTP TO HTTPS REDIRECT (Commented out - using simple HTTP listener in main.tf)
# =============================================================================

# resource "aws_lb_listener" "sbh_http_redirect" {
#   load_balancer_arn = aws_lb.sbh_alb.arn
#   port              = "80"
#   protocol          = "HTTP"

#   default_action {
#     type = "redirect"

#     redirect {
#       port        = "443"
#       protocol    = "HTTPS"
#       status_code = "HTTP_301"
#     }
#   }

#   tags = {
#     Name        = "${var.project_name}-http-redirect-${var.environment}"
#     Environment = var.environment
#     Project     = var.project_name
#   }
# }
