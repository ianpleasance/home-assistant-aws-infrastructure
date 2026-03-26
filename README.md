# AWS Infrastructure Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A comprehensive Home Assistant integration for monitoring your AWS infrastructure. Monitor only the services you use — a minimum IAM policy is generated automatically during setup.

## Features

- **28 AWS Services** — choose only the ones you need during setup
- **Minimum IAM policy** — generated automatically for your selection, shown before you finish setup
- **Multi-region** — all regions or specific regions
- **Dynamic sensors** — appear as resources are discovered, removed when deleted
- **Rich attributes** — IPs, VPC, encryption, backup retention, billing mode, key age, and much more
- **Cost tracking** — daily and month-to-date with per-service breakdown
- **Security visibility** — IAM hygiene, certificate expiry, CloudTrail status
- **Ready-made dashboards** — simple overview and detailed per-service tabs included

## Services

| Category | Services |
|----------|---------|
| **Compute** | EC2, Lambda, Auto Scaling, ECS, EKS, Elastic Beanstalk |
| **Databases & Storage** | RDS, Redshift, DynamoDB, ElastiCache, S3, EBS, EFS, ECR |
| **Networking** | VPC, ALB/NLB, Classic LB, Elastic IPs, API Gateway, CloudFront, Route 53 |
| **Messaging** | SNS, SQS, Kinesis |
| **Security** | IAM, ACM Certificates, CloudTrail |
| **Monitoring & Cost** | CloudWatch Alarms, Cost Explorer |

## Installation

### Via HACS (Recommended)

1. Open HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/ianpleasance/home-assistant-aws-infrastructure` — Category: Integration
3. Search **AWS Infrastructure Monitor** → **Download**
4. Restart Home Assistant

### Manual

1. Copy `custom_components/aws_infrastructure` to your `config/custom_components/` directory
2. Restart Home Assistant

## Setup

Go to **Settings → Devices & Services → + Add Integration → AWS Infrastructure Monitor**

The setup has up to four steps:

1. **Credentials** — account name, Access Key ID, Secret Access Key, region mode, refresh interval
2. **Regions** *(if "Select specific regions" chosen)* — pick which regions to monitor
3. **Services** — select which AWS services to monitor. Use **★ Select All Services** to enable everything, or pick individually. Services are grouped by category
4. **IAM Policy** — the minimum IAM policy for your selection is displayed. Copy and apply this to your IAM user before clicking Finish

## Changing Services After Setup

Go to **Settings → Devices & Services → AWS Infrastructure → Configure**

You can add or remove services at any time. If you add a service that requires new IAM permissions, the additional actions needed are shown before saving. Removing a service automatically deletes its sensors.

## IAM Policy

See [IAM_POLICY.md](IAM_POLICY.md) for the complete reference including per-service permission blocks.

The complete policy for all 28 services:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "HomeAssistantAWSMonitoring",
            "Effect": "Allow",
            "Action": [
                "acm:DescribeCertificate",
                "acm:ListCertificates",
                "apigateway:GET",
                "autoscaling:DescribeAutoScalingGroups",
                "ce:GetCostAndUsage",
                "cloudfront:ListDistributions",
                "cloudtrail:DescribeTrails",
                "cloudtrail:GetEventSelectors",
                "cloudtrail:GetTrailStatus",
                "cloudwatch:DescribeAlarms",
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
                "ec2:DescribeAddresses",
                "ec2:DescribeInstances",
                "ec2:DescribeInternetGateways",
                "ec2:DescribeNatGateways",
                "ec2:DescribeRegions",
                "ec2:DescribeSubnets",
                "ec2:DescribeVolumes",
                "ec2:DescribeVpcPeeringConnections",
                "ec2:DescribeVpcs",
                "ec2:DescribeVpnConnections",
                "ecr:DescribeImages",
                "ecr:DescribeRepositories",
                "ecs:DescribeClusters",
                "ecs:ListClusters",
                "eks:DescribeCluster",
                "eks:ListClusters",
                "elasticache:DescribeCacheClusters",
                "elasticbeanstalk:DescribeEnvironments",
                "elasticfilesystem:DescribeFileSystems",
                "elasticloadbalancing:DescribeLoadBalancers",
                "iam:GenerateCredentialReport",
                "iam:GetAccountPasswordPolicy",
                "iam:GetAccountSummary",
                "iam:GetCredentialReport",
                "iam:ListRoles",
                "kinesis:DescribeStreamSummary",
                "kinesis:ListStreams",
                "lambda:ListFunctions",
                "rds:DescribeDBInstances",
                "redshift:DescribeClusters",
                "route53:ListHostedZones",
                "s3:GetBucketLocation",
                "s3:ListAllMyBuckets",
                "sns:GetTopicAttributes",
                "sns:ListTopics",
                "sqs:GetQueueAttributes",
                "sqs:ListQueues",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

> ⚠️ **Cost Explorer charges $0.01 per API call** (~$0.60/month at default 24h refresh). Deselect Cost Explorer during setup if not needed.

## Documentation

- [Sensor Reference (SENSORS.md)](SENSORS.md) — every sensor, its native value, and all attributes
- [IAM Policy Reference (IAM_POLICY.md)](IAM_POLICY.md) — per-service IAM permissions

## Changelog

### v1.8.0 (2026-03-26)
- ✨ Service selection during setup — monitor only the services you use
- ✨ Minimum IAM policy generated automatically and displayed during setup
- ✨ New IAM permissions shown when adding services via options flow
- ✨ Removing a service automatically cleans up its sensors
- ✨ Added `IAM_POLICY.md` — complete per-service IAM permission reference
- ✨ Enhanced attributes: EC2 (IP, VPC, security groups), RDS (endpoint, multi-AZ, deletion protection), Lambda (architecture, layers), ElastiCache (encryption), SQS (retention, FIFO), DynamoDB (billing mode, indexes), ASG (launch template, AZs)

### v1.6.12 (2026-03-25)
- 🐛 Fixed IAM credential report loop indentation (only last user was being processed)
- 🐛 Fixed duplicate aggregation blocks for CloudTrail, ACM, ECR, Redshift, IAM
- 🐛 Fixed duplicate ACM and ECR elif blocks in entity registration and stale cleanup
- 🐛 Fixed IAM role filtering to exclude /service-role/ paths and aws-/Amazon/AWS name prefixes
- 🐛 Fixed dashboard entity IDs for IAM sensors (global device prefix)
- 🐛 Fixed stale sensor cleanup — owned set now seeded from entity registry
- 🐛 Fixed dashboard loops to exclude unavailable/unknown sensors
- 🐛 Fixed RDS/EFS phantom entries in dashboard loops
- ✨ Redshift cluster monitoring
- ✨ IAM monitoring — user hygiene, roles, password policy, root account

## License

Apache License 2.0
