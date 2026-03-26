# AWS Infrastructure Monitor

Monitor your AWS infrastructure from Home Assistant — only the services you actually use, with a minimum IAM policy generated automatically during setup.

## 🚀 27 AWS Services

| Category | Services |
|----------|---------|
| **Compute** | EC2, Lambda, Auto Scaling, ECS, EKS, Beanstalk |
| **Databases & Storage** | RDS, DynamoDB, ElastiCache, S3, EBS, EFS, ECR |
| **Networking** | VPC, ALB/NLB, Classic LB, Elastic IPs, API Gateway, CloudFront, Route 53 |
| **Messaging** | SNS, SQS, Kinesis |
| **Security** | IAM, ACM Certificates, CloudTrail |
| **Monitoring & Cost** | CloudWatch Alarms, Cost Explorer |

## ⚙️ Setup

1. Add integration via **Settings → Devices & Services → + Add Integration**
2. Enter credentials and select regions
3. **Select which services to monitor** — use ★ Select All or pick individually
4. **Copy the generated IAM policy** — minimum permissions for your selection shown automatically

## 🔒 Least-Privilege IAM

The integration generates the minimum IAM policy for your selected services. No unnecessary permissions. Change your service selection any time via **Configure** — entities are cleaned up automatically.

## 💰 Cost Explorer Note

AWS charges **$0.01 per Cost Explorer API call**. Default 24h refresh = ~$0.60/month. Only enable if you want cost tracking.

## 📝 What's New in v1.6.7

- ✨ Select which services to monitor during setup
- ✨ Minimum IAM policy auto-generated for your selection
- ✨ Add/remove services any time via Configure
- 🔒 Least-privilege by default

## 🔗 Links

- [Full Documentation](https://github.com/ianpleasance/home-assistant-aws-infrastructure)
- [Report Issues](https://github.com/ianpleasance/home-assistant-aws-infrastructure/issues)
