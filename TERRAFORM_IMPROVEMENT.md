# Terraform Infrastructure Module for MasterClaw

## Summary

Added a complete Terraform Infrastructure as Code (IaC) module for deploying MasterClaw to AWS. This addresses a significant gap where users previously had to manually configure cloud infrastructure or use Docker Compose locally.

## Problem

Previously, deploying MasterClaw to the cloud required:
1. Manually creating VPC, subnets, and networking
2. Manually configuring EKS or other Kubernetes clusters
3. Manually setting up RDS, ElastiCache, and other data stores
4. Manually configuring load balancers and SSL certificates
5. No reproducible, version-controlled infrastructure

## Solution

Created a comprehensive Terraform module with:

### Module Structure
```
terraform/
├── modules/masterclaw/          # Reusable module
│   ├── vpc/                     # VPC with public/private/database subnets
│   ├── eks/                     # EKS cluster with managed node groups
│   ├── rds/                     # PostgreSQL with Multi-AZ and encryption
│   ├── elasticache/             # Redis cluster with auth
│   ├── s3/                      # Encrypted S3 buckets for backups
│   ├── alb/                     # Application Load Balancer with SSL
│   ├── templates/               # Helm values templates
│   ├── README.md                # Module documentation
│   ├── versions.tf              # Provider versions
│   ├── variables.tf             # Input variables
│   ├── main.tf                  # Module orchestration
│   └── outputs.tf               # Output values
└── environments/
    ├── dev/                     # Development environment
    ├── staging/                 # Staging environment
    └── prod/                    # Production environment
```

### Features

#### 1. VPC Module
- Multi-AZ VPC with public, private, and database subnets
- NAT Gateways (single for dev, multi for prod)
- VPC Flow Logs for network monitoring
- Proper route tables and associations

#### 2. EKS Module
- Managed Kubernetes cluster (EKS)
- Managed node groups with auto-scaling
- Support for spot instances (cost optimization)
- IRSA (IAM Roles for Service Accounts)
- KMS encryption for secrets

#### 3. RDS Module
- PostgreSQL 16 with Multi-AZ support
- Automated backups with configurable retention
- Encryption at rest using KMS
- Performance Insights enabled
- CloudWatch alarms for CPU and storage

#### 4. ElastiCache Module
- Redis 7.0 cluster mode
- Auth token authentication
- Encryption in transit and at rest
- Multi-AZ support for production
- CloudWatch monitoring

#### 5. S3 Module
- Encrypted S3 buckets for backups
- Versioning enabled
- Lifecycle policies for cost optimization
- CORS configuration for file uploads
- Separate buckets for logs and assets

#### 6. ALB Module
- Application Load Balancer with SSL/TLS
- ACM certificate management
- Route53 integration
- Health checks configured
- Access logging to S3

### Environment Configurations

#### Development
```bash
cd terraform/environments/dev
terraform init
terraform plan
terraform apply
```
- Single NAT Gateway for cost savings
- Single-node Redis
- t3.medium instances
- 7-day log retention

#### Staging
- Similar to dev but with HA Redis
- Larger instance types
- 30-day log retention

#### Production
```bash
cd terraform/environments/prod
terraform init
terraform plan
terraform apply
```
- Multi-AZ for all data stores
- Multi-NAT Gateway
- m6i.large instances
- 30-day backup retention
- 90-day log retention
- Deletion protection enabled

### Inputs

| Name | Description | Default | Required |
|------|-------------|---------|----------|
| `cluster_name` | EKS cluster name | `"masterclaw"` | no |
| `environment` | Environment name | `"prod"` | no |
| `vpc_cidr` | VPC CIDR block | `"10.0.0.0/16"` | no |
| `domain_name` | Domain name | - | yes |
| `acme_email` | Email for SSL | - | yes |
| `gateway_token` | OpenClaw Gateway token | - | yes |
| `openai_api_key` | OpenAI API key | `""` | no |

### Outputs

| Name | Description |
|------|-------------|
| `cluster_endpoint` | EKS cluster endpoint |
| `database_endpoint` | RDS endpoint |
| `redis_endpoint` | Redis endpoint |
| `backup_bucket_name` | S3 backup bucket |
| `masterclaw_url` | MasterClaw URL |
| `kubeconfig_command` | kubectl setup command |

### Security Features

- All data encrypted at rest using KMS
- SSL/TLS for all external connections
- Private subnets for compute and data
- Security groups with least privilege
- IAM roles with IRSA for pods
- VPC Flow Logs for network monitoring
- S3 buckets with encryption and versioning

### Cost Optimization

- Spot instances support for EKS nodes
- Auto-scaling for all node groups
- Single NAT Gateway option for dev
- RDS storage auto-scaling
- S3 lifecycle policies

## Usage

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform >= 1.0 installed
3. kubectl installed
4. helm installed

### Quick Start

```bash
# 1. Navigate to environment
cd terraform/environments/dev

# 2. Copy and edit terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
# Edit with your values

# 3. Initialize Terraform
terraform init

# 4. Plan the deployment
terraform plan

# 5. Apply the deployment
terraform apply

# 6. Configure kubectl
aws eks update-kubeconfig --name masterclaw-dev --region us-east-1

# 7. Verify deployment
kubectl get pods -n masterclaw
```

### Example terraform.tfvars

```hcl
gateway_token     = "your-secure-gateway-token-here"
openai_api_key    = "sk-..."
anthropic_api_key = "sk-ant-..."
```

## Files Added

1. `terraform/modules/masterclaw/README.md` - Module documentation
2. `terraform/modules/masterclaw/versions.tf` - Provider constraints
3. `terraform/modules/masterclaw/variables.tf` - Input variables (~190 lines)
4. `terraform/modules/masterclaw/main.tf` - Main module orchestration (~250 lines)
5. `terraform/modules/masterclaw/outputs.tf` - Output definitions (~100 lines)
6. `terraform/modules/masterclaw/vpc/main.tf` - VPC module (~200 lines)
7. `terraform/modules/masterclaw/eks/main.tf` - EKS module (~200 lines)
8. `terraform/modules/masterclaw/rds/main.tf` - RDS module (~150 lines)
9. `terraform/modules/masterclaw/elasticache/main.tf` - Redis module (~120 lines)
10. `terraform/modules/masterclaw/s3/main.tf` - S3 module (~150 lines)
11. `terraform/modules/masterclaw/alb/main.tf` - ALB module (~200 lines)
12. `terraform/modules/masterclaw/templates/values.yaml.tpl` - Helm values template
13. `terraform/environments/dev/main.tf` - Dev environment
14. `terraform/environments/dev/variables.tf` - Dev variables
15. `terraform/environments/staging/main.tf` - Staging environment
16. `terraform/environments/staging/variables.tf` - Staging variables
17. `terraform/environments/prod/main.tf` - Production environment
18. `terraform/environments/prod/variables.tf` - Production variables

## Benefits

1. **Infrastructure as Code** - Version-controlled, reproducible infrastructure
2. **Multi-Environment Support** - Dev, staging, and production configurations
3. **Security by Default** - Encryption, private subnets, least privilege IAM
4. **Cost Optimization** - Spot instances, auto-scaling, lifecycle policies
5. **High Availability** - Multi-AZ support for production workloads
6. **Automated SSL** - ACM certificate management with Route53
7. **Monitoring Ready** - CloudWatch logs, flow logs, and alarms

## Future Enhancements

- Add GCP and Azure provider support
- Add Terraform Cloud/Enterprise integration
- Add drift detection workflows
- Add cost estimation integration
- Add policy-as-code (OPA/Sentinel)
