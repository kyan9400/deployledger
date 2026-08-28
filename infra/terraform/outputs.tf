output "ecs_cluster_name" {
  value       = aws_ecs_cluster.this.name
  description = "ECS cluster hosting DeployLedger."
}

output "api_repository_url" {
  value       = aws_ecr_repository.api.repository_url
  description = "Push target for the API image."
}

output "web_repository_url" {
  value       = aws_ecr_repository.web.repository_url
  description = "Push target for the web image."
}

