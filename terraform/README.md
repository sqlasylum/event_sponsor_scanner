# Terraform Modules

Two deployment targets are provided. Choose one.

## Option A — Local (Docker Compose)

Requires: Docker, Docker Compose, Terraform ≥ 1.5

```bash
cd terraform/local
terraform init
terraform apply -var="project_root=$(pwd)/../.."
```

This runs `docker compose up -d --build` in the project root. The service will be available at http://localhost:8000.

To tear down:
```bash
terraform destroy -var="project_root=$(pwd)/../.."
```

## Option B — AWS ECS Fargate + RDS

Requires: AWS CLI configured, Terraform ≥ 1.5, an ACM certificate for your domain (optional but recommended for HTTPS).

```bash
cd terraform/modules/aws_fargate

# Create a terraform.tfvars file (NOT committed to git):
cat > terraform.tfvars <<EOF
db_password         = "your-strong-password"
secret_key          = "$(openssl rand -hex 32)"
domain_name         = "scan.example.com"
acm_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/..."
EOF

terraform init
terraform apply
```

After apply, push your Docker image using the `push_commands` output:
```bash
terraform output -raw push_commands | bash
```

Then force a new ECS deployment:
```bash
aws ecs update-service --cluster event-scanner --service event-scanner --force-new-deployment
```

## Option C — AWS EC2 (single VM)

Simpler and cheaper for small events.

```bash
cd terraform/modules/aws_ec2

cat > terraform.tfvars <<EOF
key_pair_name = "your-ec2-key-pair"
db_password   = "your-strong-password"
secret_key    = "$(openssl rand -hex 32)"
base_url      = "http://YOUR_IP"
EOF

terraform init
terraform apply
```

The instance will clone this repository and start via Docker Compose automatically.
Update `user_data.sh` with your actual git repository URL before deploying.
