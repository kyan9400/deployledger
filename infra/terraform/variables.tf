variable "aws_region" {
  description = "AWS region for the ECS service."
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "staging"
}

variable "vpc_id" {
  description = "Existing VPC where ECS tasks run."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for Fargate tasks."
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security groups allowing traffic to the tasks."
  type        = list(string)
}

variable "image_tag" {
  description = "Immutable image tag published to GHCR or mirrored to ECR."
  type        = string
}

variable "database_url_secret_arn" {
  description = "Secrets Manager ARN containing DEPLOYLEDGER_DATABASE_URL."
  type        = string
  sensitive   = true
}

variable "api_key_secret_arn" {
  description = "Secrets Manager ARN containing DEPLOYLEDGER_API_KEY."
  type        = string
  sensitive   = true
}

variable "webhook_secret_arn" {
  description = "Secrets Manager ARN containing DEPLOYLEDGER_WEBHOOK_SECRET."
  type        = string
  sensitive   = true
}

