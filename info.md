# AWS Infrastructure Monitor

Monitor your entire AWS infrastructure from Home Assistant! Track 23 AWS services, costs, and resources across multiple regions.

## 🚀 Features

### 23 AWS Services Monitored
- **Compute**: EC2, Lambda, ECS, EKS, Auto Scaling Groups, Elastic Beanstalk
- **Data & Storage**: RDS, DynamoDB, ElastiCache, S3, EBS Volumes, EFS
- **Networking**: ALB/NLB Load Balancers, Classic Load Balancers, Elastic IPs, SNS, SQS, Kinesis
- **APIs & CDN**: API Gateway (REST + HTTP/WebSocket), CloudFront, Route 53
- **Monitoring**: CloudWatch Alarms

### 💰 Cost Tracking
- Daily and month-to-date AWS costs
- Top 10 services by spend with percentage breakdown
- Configurable refresh to minimise API costs (default: $0.60/month)

### 🌍 Multi-Region Support
- Monitor all AWS regions or select specific ones
- Global summary sensor aggregating resources across all regions
- Regional summaries for each monitored region
- CloudFront and Route 53 detected as global services (fetched via us-east-1)

### 📊 Individual Resource Tracking
- Sensor for each EC2 instance, Lambda function, RDS database, load balancer, etc.
- Detailed attributes and state tracking per resource
- Historical data for trends and alerts
- Automatic entity creation and cleanup

## ⚙️ Quick Start

1. Create AWS IAM user with required permissions (see [README](https://github.com/ianpleasance/home-assistant-aws-infrastructure#configuration))
2. Add integration via **Settings → Devices & Services → + Add Integration**
3. Search for "AWS Infrastructure Monitor", enter your AWS credentials and select regions
4. Configure refresh intervals (resources: 5 min default, costs: 24 h default)

## 💡 Example Use Cases

- **Cost Alerts**: Get notified when daily costs exceed a threshold
- **Resource Monitoring**: Track EC2 instances, databases, functions, and containers
- **Optimisation**: Find unattached Elastic IPs and EBS volumes costing money
- **Compliance**: Monitor CloudWatch alarms, encryption status, and resource states
- **Capacity Planning**: Track Auto Scaling Groups, ECS/EKS clusters, and Beanstalk environments
- **DNS & CDN**: Monitor Route 53 hosted zones and CloudFront distribution health
- **API Visibility**: Track all API Gateway deployments (REST and HTTP/WebSocket)

## 💰 Cost Optimisation

**Important**: AWS Cost Explorer charges $0.01 per API call.

Default configuration: **24-hour refresh = ~$0.60/month**

⚠️ Setting to 5-minute refresh = ~$172/month — not recommended!

## 🌍 Supported Languages

English • French • German • Italian • Spanish • Dutch • Swedish • Norwegian • Danish • Polish • Portuguese • Finnish • Japanese

## 📊 Included Dashboards

Two pre-built dashboards in the `dashboards/` folder:

- **DASHBOARD_simple.yaml** — Single-page overview with global summary, cost tracking, and per-region breakdowns for all 23 services
- **DASHBOARD_detailed.yaml** — Full multi-tab dashboard with a dedicated tab per service group: EC2, Lambda, RDS, DynamoDB, ElastiCache, Containers, Storage, Messaging, Networking, API & CDN, Beanstalk, ASG, Monitoring, and Costs

## 🔧 IAM Policy Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeRegions",
        "ec2:DescribeVolumes",
        "ec2:DescribeAddresses",
        "rds:DescribeDBInstances",
        "lambda:ListFunctions",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTags",
        "autoscaling:DescribeAutoScalingGroups",
        "dynamodb:ListTables",
        "dynamodb:DescribeTable",
        "elasticache:DescribeCacheClusters",
        "ecs:ListClusters",
        "ecs:DescribeClusters",
        "eks:ListClusters",
        "eks:DescribeCluster",
        "sns:ListTopics",
        "sns:GetTopicAttributes",
        "sqs:ListQueues",
        "sqs:GetQueueAttributes",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "elasticfilesystem:DescribeFileSystems",
        "cloudwatch:DescribeAlarms",
        "apigateway:GET",
        "cloudfront:ListDistributions",
        "route53:ListHostedZones",
        "kinesis:ListStreams",
        "kinesis:DescribeStreamSummary",
        "elasticbeanstalk:DescribeEnvironments",
        "ce:GetCostAndUsage"
      ],
      "Resource": "*"
    }
  ]
}
```

## 📈 Sensors Created

- **Global Summary** — Total resources across all regions with per-service breakdown attributes
- **Regional Summaries** — Per-region resource counts and breakdowns
- **Cost Sensors** — Yesterday, month-to-date, and top 10 per-service costs
- **Individual Resources** — Sensor for each EC2 instance, RDS database, Lambda function, load balancer, EFS file system, Kinesis stream, Beanstalk environment, CloudFront distribution, Route 53 zone, API Gateway, and more
- **Count Sensors** — Optional per-service count sensors for history graphs

## 📝 What's New in v1.4.0

- ✨ **Classic Load Balancer** detection and monitoring (alongside existing ALB/NLB support)
- ✨ **API Gateway** — REST (v1) and HTTP/WebSocket (v2) APIs
- ✨ **CloudFront** — Global CDN distribution monitoring
- ✨ **EFS** — Elastic File System monitoring
- ✨ **Route 53** — Global hosted zone monitoring
- ✨ **Kinesis** — Data stream monitoring with shard count and retention
- ✨ **Elastic Beanstalk** — Environment health (Green/Yellow/Red), status, tier, and endpoints
- 📊 Updated both dashboards with all new services
- 📖 Updated README and IAM policy documentation

## 🔗 Links

- [Full Documentation](https://github.com/ianpleasance/home-assistant-aws-infrastructure)
- [Report Issues](https://github.com/ianpleasance/home-assistant-aws-infrastructure/issues)

---

**⭐ Star the repo if you find this useful!**
