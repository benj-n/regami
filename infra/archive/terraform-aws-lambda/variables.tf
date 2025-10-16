# Terraform Configuration for Serverless Infrastructure

terraform {
  required_version = ">= 1.5"
}

# Variables file
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "regami"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

# Outputs example
output "deployment_instructions" {
  value = <<-EOT

    🚀 Serverless Infrastructure Deployment Guide
    ============================================

    ## Prerequisites

    1. Install Terraform >= 1.5
    2. Configure AWS credentials:
       export AWS_ACCESS_KEY_ID=xxx
       export AWS_SECRET_ACCESS_KEY=xxx

    3. Create S3 bucket for Terraform state:
       aws s3 mb s3://regami-terraform-state --region us-east-1

    ## Deployment Steps

    1. Initialize Terraform:
       cd infra/terraform-serverless
       terraform init

    2. Review the plan:
       terraform plan

    3. Apply infrastructure:
       terraform apply

    4. Deploy Lambda code:
       cd ../../backend
       ./build-lambda.sh
       aws lambda update-function-code \
         --function-name regami-api \
         --zip-file fileb://lambda_deployment.zip

    5. Test the deployment:
       curl https://$(terraform output -raw api_gateway_url)/health

    ## Cost Monitoring

    Monitor your costs with:
    - AWS Cost Explorer
    - CloudWatch billing alarms
    - Set budget alerts at $30/month

    ## Expected Costs (Low Traffic)

    - Lambda: $2-5/month
    - API Gateway: $1-3/month
    - Aurora Serverless v2: $10-30/month
    - S3: $1-3/month
    - CloudFront: $1-2/month
    - CloudWatch: $1-2/month

    TOTAL: $16-45/month (vs $250-400 with ECS/RDS)
    SAVINGS: 82-89% reduction!

  EOT
}
