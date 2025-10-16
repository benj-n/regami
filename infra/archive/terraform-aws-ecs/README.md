# AWS IaC (Terraform)# AWS Deployment (Terraform)



This folder provisions AWS infrastructure for Regami using Terraform:This folder contains a minimal Terraform stack to run Regami on AWS:

- ECR repos for api and web- VPC (public/private subnets)

- ECS Fargate cluster with services/tasks for API and Web- ECS (Fargate) + ALB

- Application Load Balancer (ALB)- RDS PostgreSQL

- RDS PostgreSQL- S3 (web static + media) + CloudFront for the web

- S3 bucket for media (dog photos)- ECR repository for backend image



## Prerequisites## Prereqs

- AWS account and credentials configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)- Terraform >= 1.5

- Terraform >= 1.6- AWS credentials configured (profile or env vars)



## Usage## Bootstrap

```bash

1. Copy `terraform.tfvars.example` to `terraform.tfvars` and fill values.cd infra/aws/terraform

2. Initialize and apply:terraform init

terraform apply -auto-approve \

```bash  -var name=regami \

cd infra/aws  -var environment=prod \

terraform init  -var aws_region=ca-central-1

terraform plan```

terraform applyOutputs will include:

```- ECR repo URL (push backend image here)

- CloudFront domain for the web

Outputs will include ALB DNS names for the API and Web services.- S3 buckets (web/media)

- ALB DNS name for the API

## Notes

- This is a minimal scaffold. Tighten security groups, IAM least privilege, and add SSL/TLS via ACM for production.## Deploy flow

- GitHub Actions workflow `.github/workflows/deploy.yml` demonstrates an automated deploy. It requires AWS credentials and variables (see secrets in that file).1) Backend image

- Build and push Docker image to ECR
- Update ECS service to use the new tag (CI does this)

2) Web
- Build `web/` and sync `dist/` to the web S3 bucket
- Invalidate CloudFront cache

3) Config/Secrets
- Put `DATABASE_URL`, `SECRET_KEY`, and SMTP creds in Secrets Manager
- Put non-secret config (CORS_ORIGINS, APP_ENV, etc.) in SSM Parameter Store

See `.github/workflows/deploy.yml` for an example pipeline.
