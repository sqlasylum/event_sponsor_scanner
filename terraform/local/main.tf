terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

variable "project_root" {
  description = "Absolute path to the project root (directory containing docker-compose.yml)"
  type        = string
  default     = "../.."
}

variable "env_file" {
  description = "Path to the .env file (relative to project_root)"
  type        = string
  default     = ".env"
}

resource "null_resource" "docker_compose_up" {
  triggers = {
    always = timestamp()
  }

  provisioner "local-exec" {
    working_dir = var.project_root
    command     = "docker compose up -d --build"
  }

  provisioner "local-exec" {
    when        = destroy
    working_dir = var.project_root
    command     = "docker compose down"
  }
}

output "service_url" {
  value = "http://localhost:8000"
}
