variable "repo_url" {
  description = "GitHub repository URL to clone onto the instance (e.g. https://github.com/your-org/event_sponsor_scanner.git)"
  type        = string
}

variable "app_name" {
  type    = string
  default = "event-scanner"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t3.small"
}

variable "key_pair_name" {
  description = "EC2 key pair name for SSH access"
  type        = string
}

variable "ssh_allowed_cidrs" {
  description = "CIDR blocks allowed to SSH into the instance"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "db_password" {
  description = "PostgreSQL password (used in docker-compose on the instance)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Secret key for signing session cookies"
  type        = string
  sensitive   = true
}

variable "base_url" {
  description = "Public URL of the service (e.g. http://1.2.3.4 or https://scan.example.com)"
  type        = string
}

variable "admin_password" {
  description = "Password for /admin/* routes (username is always 'admin')"
  type        = string
  sensitive   = true
}

variable "event_name" {
  description = "Display name shown on the status page"
  type        = string
  default     = "Event Sponsor Scanner"
}
