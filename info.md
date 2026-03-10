# AWS Infrastructure Monitor

Monitor your entire AWS infrastructure from Home Assistant! Track 15 AWS services, costs, and resources across multiple regions.

## 🚀 Features

### 15 AWS Services Monitored
- **Compute**: EC2, Lambda, ECS, EKS, Auto Scaling Groups
- **Data & Storage**: RDS, DynamoDB, ElastiCache, S3, EBS Volumes
- **Networking**: Load Balancers, Elastic IPs, SNS, SQS
- **Monitoring**: CloudWatch Alarms

### 💰 Cost Tracking
- Daily and month-to-date AWS costs
- Top 10 services by spend
- Configurable refresh to minimize API costs (default: $0.60/month)

### 🌍 Multi-Region Support
- Monitor all AWS regions or select specific ones
- Global summary across all regions
- Regional summaries for each monitored region

### 📊 Individual Resource Tracking
- Sensor for each EC2 instance, Lambda function, RDS database, etc.
- Detailed attributes and state tracking
- Historical data for trends and alerts

## ⚙️ Quick Start

1. Create AWS IAM user with required permissions (see [README](https://github.com/ianpleasance/home-assistant-aws-infrastructure#configuration))
2. Add integration via Settings → Devices & Services
3. Enter AWS credentials and select regions
4. Configure refresh intervals (resources: 5min, costs: 24h)

## 💡 Example Use Cases

- **Cost Alerts**: Get notified when daily costs exceed threshold
- **Resource Monitoring**: Track EC2 instances, databases, functions
- **Optimization**: Find unattached Elastic IPs costing money
- **Compliance**: Monitor CloudWatch alarms and resource states
- **Capacity Planning**: Track Auto Scaling Groups and ECS clusters

## 💰 Cost Optimization

**Important**: AWS Cost Explorer charges $0.01 per API call.

Default configuration: **24-hour refresh = $0.60/month**

⚠️ Setting to 5-minute refresh = $172.80/month!

## 🌍 Supported Languages

English • French • German • Italian • Spanish • Dutch • Swedish • Norwegian • Danish • Polish • Portuguese • Finnish • Japanese

## 📊 Sample Dashboard

Pre-built dashboards included:
- Simple overview with cost tracking
- Detailed multi-tab dashboard with all services
- Regional breakdowns

## 🔧 IAM Policy Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "lambda:List*",
        "elasticloadbalancing:Describe*",
        "autoscaling:Describe*",
        "dynamodb:List*",
        "dynamodb:Describe*",
        "elasticache:Describe*",
        "ecs:List*",
        "ecs:Describe*",
        "eks:List*",
        "eks:Describe*",
        "sns:List*",
        "sns:Get*",
        "sqs:List*",
        "sqs:Get*",
        "s3:ListAllMyBuckets",
        "s3:GetBucket*",
        "cloudwatch:Describe*",
        "ce:GetCostAndUsage"
      ],
      "Resource": "*"
    }
  ]
}
```

## 📈 Sensors Created

- **Global Summary**: Total resources across all regions
- **Regional Summaries**: Per-region resource counts
- **Cost Sensors**: Yesterday, MTD, and per-service costs
- **Individual Resources**: Sensor for each EC2, RDS, Lambda, etc.
- **Count Sensors**: Optional count sensors for history graphs

## 🔗 Links

- [Full Documentation](https://github.com/ianpleasance/home-assistant-aws-infrastructure)
- [Report Issues](https://github.com/ianpleasance/home-assistant-aws-infrastructure/issues)
- [Sample Dashboards](https://github.com/ianpleasance/home-assistant-aws-infrastructure/tree/main/examples)

## 📝 Recent Updates (v1.2.0)

- 🐛 Fixed EC2 count sensor bug (instance data structure)
- 🔧 Migrated all device_info to HA DeviceInfo class
- ✅ Added last_updated native datetime to all sensors
- 🌍 13 language translations (da, de, en, es, fi, fr, it, ja, nl, no, pl, pt, sv)
- 🔧 Standardised logging to %s style

---

**⭐ Star the repo if you find this useful!**

