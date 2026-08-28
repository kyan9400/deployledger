# Terraform deployment blueprint

This module provisions the AWS primitives for a small production-like DeployLedger environment: immutable ECR repositories, an ECS Fargate cluster, CloudWatch logs, least-privilege task roles, and a circuit-breaker-enabled API service.

It intentionally consumes an existing VPC, private subnets, security groups, and Secrets Manager entries. That keeps network boundaries and secret ownership with the platform team instead of hiding them in an application module.

```powershell
terraform init
terraform fmt -check
terraform validate
terraform plan `
  -var='vpc_id=vpc-...' `
  -var='private_subnet_ids=["subnet-...","subnet-..."]' `
  -var='security_group_ids=["sg-..."]' `
  -var='image_tag=0.1.0' `
  -var='database_url_secret_arn=arn:aws:secretsmanager:...' `
  -var='api_key_secret_arn=arn:aws:secretsmanager:...' `
  -var='webhook_secret_arn=arn:aws:secretsmanager:...'
```

This is a blueprint, not an instruction to apply against an account. Review IAM, egress, WAF, database backups, and load-balancer configuration with the owning platform team first.

