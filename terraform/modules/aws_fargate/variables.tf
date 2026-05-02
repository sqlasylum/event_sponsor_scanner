variable "app_name" {
  description = "Application name used for resource naming"
  type        = string
  default     = "event-scanner"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Secret key for signing session cookies (openssl rand -hex 32)"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Public domain name for the service (e.g. scan.example.com)"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS. Leave empty to use HTTP only."
  type        = string
  default     = ""
}

variable "task_count" {
  description = "Number of ECS Fargate tasks to run"
  type        = number
  default     = 1
}
