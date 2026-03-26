# AWS Infrastructure Monitor

Monitor your AWS infrastructure from Home Assistant. Track resources across 28 services and multiple regions, with individual sensors for every resource and ready-made dashboards included.

## 🚀 28 AWS Services

| Category | Services |
|----------|---------|
| **Compute** | EC2, Lambda, Auto Scaling, ECS, EKS, Elastic Beanstalk |
| **Databases & Storage** | RDS, Redshift, DynamoDB, ElastiCache, S3, EBS, EFS, ECR |
| **Networking** | VPC, ALB/NLB Load Balancers, Classic Load Balancers, Elastic IPs, API Gateway, CloudFront, Route 53 |
| **Messaging & Streaming** | SNS, SQS, Kinesis |
| **Security & Compliance** | IAM, ACM Certificates, CloudTrail |
| **Monitoring & Cost** | CloudWatch Alarms, Cost Explorer |

## ⚙️ Setup

1. Add integration via **Settings → Devices & Services → + Add Integration → AWS Infrastructure Monitor**
2. Enter your AWS Access Key ID and Secret Access Key
3. Choose to monitor all regions or select specific ones
4. Integration starts discovering your resources immediately

## 🔒 IAM Policy

Create a dedicated IAM user with **programmatic access only** and attach the following policy.

> ⚠️ **Cost Explorer charges $0.01 per API call.** Default 24h refresh = ~$0.60/month. Remove `ce:GetCostAndUsage` if you don't need cost tracking.

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

## 📊 What You Get

- **Individual sensors** for every resource — EC2 instances, Lambda functions, RDS databases, S3 buckets, and more
- **Rich attributes** on every sensor — IPs, VPC, encryption status, backup retention, billing mode, and much more
- **Regional summary sensors** with resource counts per region
- **Global summary sensor** with totals across all regions and regions
- **Security visibility** — IAM user hygiene, MFA status, access key age, certificate expiry, CloudTrail logging
- **Cost tracking** — yesterday's spend and month-to-date, broken down by top 10 services
- **Ready-made dashboards** — simple overview and detailed per-service tab dashboards included in the repo

## 💰 Cost Explorer Note

AWS charges **$0.01 per Cost Explorer API call**. The default refresh interval is 24 hours (~$0.60/month). You can increase this interval in the integration options, or remove `ce:GetCostAndUsage` from the IAM policy to disable cost tracking entirely.

## 🔗 Links

- [Full Documentation & README](https://github.com/ianpleasance/home-assistant-aws-infrastructure)
- [Sensor Reference (SENSORS.md)](https://github.com/ianpleasance/home-assistant-aws-infrastructure/blob/main/SENSORS.md)
- [Report Issues](https://github.com/ianpleasance/home-assistant-aws-infrastructure/issues)
