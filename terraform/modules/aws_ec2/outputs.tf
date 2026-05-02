output "public_ip" {
  description = "Elastic IP address of the EC2 instance"
  value       = aws_eip.app.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh ubuntu@${aws_eip.app.public_ip}"
}

output "service_url" {
  description = "Public URL of the service"
  value       = var.base_url
}
