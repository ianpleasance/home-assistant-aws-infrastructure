# AWS Infrastructure Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A comprehensive Home Assistant integration for monitoring your AWS infrastructure across multiple regions. Monitor only the services you use, with a minimum IAM policy generated automatically during setup.

## Features

- **27 AWS Services** — monitor only the ones you need
- **Multi-region** — all regions or specific regions
- **Dynamic sensors** — appear as resources are discovered, removed when deleted
- **Minimum IAM policy** — generated automatically for your selection during setup
- **Cost tracking** — daily and month-to-date with per-service breakdown
- **Security visibility** — IAM hygiene, certificate expiry, CloudTrail status

### Services Available

| Category | Services |
|----------|---------|
| **Compute** | EC2, Lambda, Auto Scaling, ECS, EKS, Elastic Beanstalk |
| **Databases & Storage** | RDS, DynamoDB, ElastiCache, S3, EBS, EFS, ECR |
| **Networking** | VPC, ALB/NLB, Classic LB, Elastic IPs, API Gateway, CloudFront, Route 53 |
| **Messaging** | SNS, SQS, Kinesis |
| **Security** | IAM, ACM Certificates, CloudTrail |
| **Monitoring & Cost** | CloudWatch Alarms, Cost Explorer |

## Installation

### Via HACS (Recommended)

1. Open HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add: `https://github.com/ianpleasance/home-assistant-aws-infrastructure`
3. Category: Integration
4. Search **AWS Infrastructure Monitor** → **Download**
5. Restart Home Assistant

### Manual

1. Copy `custom_components/aws_infrastructure` to `config/custom_components/`
2. Restart Home Assistant

## Configuration

### 1. Setup Flow

Go to **Settings → Devices & Services → + Add Integration → AWS Infrastructure Monitor**

The setup has four steps:

1. **Credentials** — account name, Access Key ID, Secret Access Key, region mode, refresh interval
2. **Regions** *(if "Select specific regions" chosen)* — pick which regions to monitor
3. **Services** — select which AWS services to monitor. Use **★ Select All Services** to enable everything, or pick individual services. Services are grouped by category for easy selection
4. **IAM Policy** — the minimum IAM policy for your selection is displayed. Copy this JSON and apply it to your IAM user before finishing setup

### 2. Create IAM User

Create a dedicated IAM user in the AWS Console with **Programmatic access** only. Apply the policy shown in step 4 of the setup flow.

The always-required permission regardless of service selection is:
```json
"sts:GetCallerIdentity"
```

### 3. Changing Services After Setup

Go to **Settings → Devices & Services → AWS Infrastructure → Configure**. You can add or remove services at any time. Removing a service deletes its sensors from HA. Adding a service creates new sensors on the next refresh. The integration reloads automatically.

## IAM Policies

### Complete Policy (All Services)

Use this if you selected **★ Select All Services**:

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

### Per-Service Policies

If you selected specific services, only include the permissions for those services. Always include `sts:GetCallerIdentity`.

##### Compute

<details><summary><b>EC2 Instances</b></summary>

```json
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
```
</details>

<details><summary><b>Lambda Functions</b></summary>

```json
                "lambda:ListFunctions",
```
</details>

<details><summary><b>Auto Scaling Groups</b></summary>

```json
                "autoscaling:DescribeAutoScalingGroups",
```
</details>

<details><summary><b>ECS Clusters</b></summary>

```json
                "ecs:DescribeClusters",
                "ecs:ListClusters",
```
</details>

<details><summary><b>EKS Clusters</b></summary>

```json
                "eks:DescribeCluster",
                "eks:ListClusters",
```
</details>

<details><summary><b>Elastic Beanstalk</b></summary>

```json
                "elasticbeanstalk:DescribeEnvironments",
```
</details>


##### Databases & Storage

<details><summary><b>RDS Databases</b></summary>

```json
                "rds:DescribeDBInstances",
                "redshift:DescribeClusters",
```
</details>

<details><summary><b>DynamoDB</b></summary>

```json
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
```
</details>

<details><summary><b>ElastiCache</b></summary>

```json
                "elasticache:DescribeCacheClusters",
```
</details>

<details><summary><b>S3 Buckets</b></summary>

```json
                "s3:GetBucketLocation",
                "s3:ListAllMyBuckets",
```
</details>

<details><summary><b>EBS Volumes</b></summary>

```json
                "ec2:DescribeVolumes",
```
</details>

<details><summary><b>EFS File Systems</b></summary>

```json
                "elasticfilesystem:DescribeFileSystems",
```
</details>

<details><summary><b>ECR Repositories</b></summary>

```json
                "ecr:DescribeImages",
                "ecr:DescribeRepositories",
```
</details>


##### Networking

<details><summary><b>VPC</b></summary>

```json
                "ec2:DescribeInternetGateways",
                "ec2:DescribeNatGateways",
                "ec2:DescribeSubnets",
                "ec2:DescribeVpcPeeringConnections",
                "ec2:DescribeVpcs",
                "ec2:DescribeVpnConnections",
```
</details>

<details><summary><b>ALB / NLB Load Balancers</b></summary>

```json
                "elasticloadbalancing:DescribeLoadBalancers",
```
</details>

<details><summary><b>Classic Load Balancers</b></summary>

```json
                "elasticloadbalancing:DescribeLoadBalancers",
```
</details>

<details><summary><b>Elastic IPs</b></summary>

```json
                "ec2:DescribeAddresses",
```
</details>

<details><summary><b>API Gateway</b></summary>

```json
                "apigateway:GET",
```
</details>

<details><summary><b>CloudFront (global)</b></summary>

```json
                "cloudfront:ListDistributions",
```
</details>

<details><summary><b>Route 53 (global)</b></summary>

```json
                "route53:ListHostedZones",
```
</details>


##### Messaging & Streaming

<details><summary><b>SNS Topics</b></summary>

```json
                "sns:GetTopicAttributes",
                "sns:ListTopics",
```
</details>

<details><summary><b>SQS Queues</b></summary>

```json
                "sqs:GetQueueAttributes",
                "sqs:ListQueues",
```
</details>

<details><summary><b>Kinesis Streams</b></summary>

```json
                "kinesis:DescribeStreamSummary",
                "kinesis:ListStreams",
```
</details>


##### Security & Compliance

<details><summary><b>IAM (global)</b></summary>

```json
                "iam:GenerateCredentialReport",
                "iam:GetAccountPasswordPolicy",
                "iam:GetAccountSummary",
                "iam:GetCredentialReport",
                "iam:ListRoles",
```
</details>

<details><summary><b>ACM Certificates</b></summary>

```json
                "acm:DescribeCertificate",
                "acm:ListCertificates",
```
</details>

<details><summary><b>CloudTrail</b></summary>

```json
                "cloudtrail:DescribeTrails",
                "cloudtrail:GetEventSelectors",
                "cloudtrail:GetTrailStatus",
```
</details>


##### Monitoring & Cost

<details><summary><b>CloudWatch Alarms</b></summary>

```json
                "cloudwatch:DescribeAlarms",
```
</details>

<details><summary><b>Cost Explorer (global)</b></summary>

```json
                "ce:GetCostAndUsage",
```
</details>


## Cost Considerations

### AWS Cost Explorer API ($0.01 per call)

| Refresh Interval | Calls/Day | Cost/Month |
|------------------|-----------|------------|
| **1440 min (24h)** | 2 | **~$0.60** ✅ Recommended |
| 720 min (12h) | 4 | ~$1.20 |
| 60 min (1h) | 48 | ~$14.40 |

All other API calls used by this integration are **free** within normal limits.

## Troubleshooting

### Credential Errors
The integration raises a persistent HA notification if credentials expire. Reconfigure via **Settings → Devices & Services → AWS Infrastructure → Configure**.

### IAM Permission Errors
A WARNING is logged once per service if a permission is missing. No further log spam. Add the missing permission to your IAM policy and the service will recover on the next refresh.

### No Sensors Appearing
Ensure the IAM policy includes all required permissions for your selected services. Check **Settings → System → Logs** for `aws_infrastructure` warnings.

## Changelog

### v1.6.9 (2026-03-25)
- ✨ Added Redshift cluster monitoring with status, node type/count, endpoint, encryption, and version

### v1.6.7 (2026-03-21)
- ✨ Service selection during setup — monitor only the services you use
- ✨ Minimum IAM policy generated automatically during setup
- ✨ Remove/add services via options flow with automatic entity cleanup
- 🔒 Integration now follows least-privilege IAM principle by default

### v1.6.6 (2026-03-21)
- 🐛 Fixed IAM credential report polling (increased retries, fixed UnboundLocalError)
- 🐛 Fixed account summary parsing

### v1.6.5 (2026-03-21)
- ✨ Added IAM monitoring: user hygiene, customer-managed roles, password policy, root account

### v1.6.4 (2026-03-21)
- 🐛 Fixed CloudTrail double-counting multi-region trails

### v1.6.3 (2026-03-21)
- ✨ Added CloudTrail monitoring

### v1.6.2 (2026-03-21)
- ✨ Added ACM certificate monitoring with expiry tracking
- ✨ Added ECR repository monitoring

### v1.6.1 (2026-03-20)
- ✨ Added VPC monitoring with subnet details

### v1.6.0 (2026-03-20)
- ✨ Added CloudFront distribution monitoring
- 🎉 All originally planned 22 services complete

## License

Apache License 2.0
