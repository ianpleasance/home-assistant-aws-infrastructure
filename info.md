# AWS Infrastructure Monitor

Monitor your entire AWS infrastructure from Home Assistant. Track 15 AWS services, costs, and resources across multiple regions.

## 🚀 Features

### 23 AWS Services Monitored
- **Compute**: EC2, Lambda, ECS, EKS, Auto Scaling Groups, Elastic Beanstalk
- **Data & Storage**: RDS, DynamoDB, ElastiCache, S3, EBS Volumes, EFS
- **Networking**: VPC, Route 53, CloudFront, API Gateway, ALB/NLB Load Balancers, Classic Load Balancers, Elastic IPs, Kinesis, SNS, SQS
- **Monitoring**: CloudWatch Alarms

### 💰 Cost Tracking
- Daily and month-to-date AWS costs
- Top 10 services by spend with percentage breakdown
- Configurable refresh to minimise API costs (default: $0.60/month)

### 🌍 Multi-Region Support
- Monitor all AWS regions or select specific ones
- Global summary sensor aggregating all regions
- Regional summaries per monitored region

### 📈 Dynamic Resource Tracking
- Sensors created automatically when new resources appear — no restart needed
- Sensors removed automatically when resources are deleted

### 🔒 Resilient & Observable
- Per-service timeouts prevent hung coordinators
- IAM permission errors warned once, then suppressed — no log spam
- Credential errors raise a persistent HA notification
- Throttling distinguished from hard errors in logs

## ⚙️ Quick Start

1. Create AWS IAM user with required permissions (see [README](https://github.com/ianpleasance/home-assistant-aws-infrastructure#configuration))
2. Add integration via **Settings → Devices & Services → + Add Integration**
3. Search for "AWS Infrastructure Monitor", enter credentials and select regions
4. Configure refresh intervals (resources: 5 min default, costs: 24 h default)

## 🔧 Minimum IAM Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "HomeAssistantAWSMonitoring",
            "Effect": "Allow",
            "Action": [
                "autoscaling:DescribeAutoScalingGroups",
                "ce:GetCostAndUsage",
                "cloudwatch:DescribeAlarms",
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
                "ec2:DescribeAddresses",
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
                "ec2:DescribeVolumes",
                "ecs:DescribeClusters",
                "ecs:ListClusters",
                "eks:DescribeCluster",
                "eks:ListClusters",
                "elasticache:DescribeCacheClusters",
                "elasticloadbalancing:DescribeLoadBalancers",
                "lambda:ListFunctions",
                "rds:DescribeDBInstances",
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

## 💰 Cost Optimisation

AWS Cost Explorer charges $0.01 per API call.

Default: **24-hour refresh = ~$0.60/month** ✅

⚠️ 5-minute refresh = ~$172/month — not recommended!

## 🌍 Supported Languages

English • French • German • Italian • Spanish • Dutch • Swedish • Norwegian • Danish • Polish • Portuguese • Finnish • Japanese

## 📝 What's New in v1.5.0

- 🔒 Proper error classification: credentials, permissions, throttling, timeouts handled differently
- 🔔 Persistent HA notification on credential failure
- 📈 Dynamic sensor registration — no restart needed when resources change
- 🧹 Automatic stale sensor cleanup when resources are deleted
- ⚡ Concurrent startup refresh — faster, more resilient
- 📋 Clean minimal IAM policy with no duplicates

## 📝 What's New in v1.5.4

- ✨ Classic Load Balancer (ELB v1) monitoring

## 📝 What's New in v1.5.5

- ✨ EFS (Elastic File System) monitoring

## 📝 What's New in v1.5.6

- ✨ Kinesis stream monitoring

## 📝 What's New in v1.5.7

- ✨ Elastic Beanstalk environment monitoring

## 📝 What's New in v1.5.8

- ✨ Route 53 hosted zone monitoring (global service)

## 📝 What's New in v1.5.9

- ✨ API Gateway monitoring (v1 REST + v2 HTTP/WebSocket)

## 📝 What's New in v1.6.0

- ✨ CloudFront distribution monitoring (global service)
- 🎉 22 planned AWS services complete

## 📝 What's New in v1.6.1

- ✨ VPC monitoring with subnet details

## 🔗 Links

- [Full Documentation](https://github.com/ianpleasance/home-assistant-aws-infrastructure)
- [Report Issues](https://github.com/ianpleasance/home-assistant-aws-infrastructure/issues)

---

**⭐ Star the repo if you find this useful!**
