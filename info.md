# AWS Infrastructure Monitor

Monitor your AWS infrastructure from Home Assistant. Select only the services you use — a minimum IAM policy is generated automatically during setup.

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
2. Enter credentials and choose regions
3. **Select which services to monitor** — use ★ Select All or pick individually by category
4. **Copy the generated IAM policy** — minimum permissions for your selection shown automatically

## 🔄 Changing Services Later

Go to **Settings → Devices & Services → AWS Infrastructure → Configure** at any time to add or remove services. Adding a service shows the new IAM permissions needed. Removing a service automatically deletes its sensors.

## 🔒 Least-Privilege IAM

The integration generates the exact minimum IAM policy for your selected services — no unnecessary permissions. All permissions are read-only; the integration never modifies your AWS resources.

See [IAM_POLICY.md](https://github.com/ianpleasance/home-assistant-aws-infrastructure/blob/main/IAM_POLICY.md) for the complete per-service permission reference.

## 💰 Cost Explorer Note

AWS charges **$0.01 per Cost Explorer API call**. Default 24h refresh = ~$0.60/month. Deselect Cost Explorer during setup if you don't need cost tracking.

## 📚 Documentation

- [Sensor Reference (SENSORS.md)](https://github.com/ianpleasance/home-assistant-aws-infrastructure/blob/main/SENSORS.md)
- [IAM Policy Reference (IAM_POLICY.md)](https://github.com/ianpleasance/home-assistant-aws-infrastructure/blob/main/IAM_POLICY.md)
- [Report Issues](https://github.com/ianpleasance/home-assistant-aws-infrastructure/issues)
