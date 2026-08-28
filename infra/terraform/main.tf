data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "api" {
  name                 = "deployledger/api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_repository" "web" {
  name                 = "deployledger/web"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/deployledger/${var.environment}/api"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "this" {
  name = "deployledger-${var.environment}"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_iam_role" "execution" {
  name = "deployledger-${var.environment}-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name = "deployledger-${var.environment}-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "task_secrets" {
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [var.database_url_secret_arn, var.api_key_secret_arn, var.webhook_secret_arn]
    }]
  })
}

resource "aws_ecs_task_definition" "api" {
  family                   = "deployledger-${var.environment}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name         = "api"
    image        = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
    essential    = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "DEPLOYLEDGER_ENVIRONMENT", value = var.environment },
      { name = "DEPLOYLEDGER_DEMO_SEED", value = "false" }
    ]
    secrets = [
      { name = "DEPLOYLEDGER_DATABASE_URL", valueFrom = var.database_url_secret_arn },
      { name = "DEPLOYLEDGER_API_KEY", valueFrom = var.api_key_secret_arn },
      { name = "DEPLOYLEDGER_WEBHOOK_SECRET", valueFrom = var.webhook_secret_arn }
    ]
    healthCheck            = { command = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')\""], interval = 30, timeout = 5, retries = 3 }
    logConfiguration       = { logDriver = "awslogs", options = { "awslogs-group" = aws_cloudwatch_log_group.api.name, "awslogs-region" = var.aws_region, "awslogs-stream-prefix" = "api" } }
    readonlyRootFilesystem = true
    user                   = "10001"
  }])
}

resource "aws_ecs_service" "api" {
  name                               = "deployledger-${var.environment}-api"
  cluster                            = aws_ecs_cluster.this.id
  task_definition                    = aws_ecs_task_definition.api.arn
  desired_count                      = 2
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}
