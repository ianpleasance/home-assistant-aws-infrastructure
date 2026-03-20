# AWS Infrastructure Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A comprehensive Home Assistant integration for monitoring your AWS infrastructure across multiple regions. Track EC2 instances, Lambda functions, RDS databases, and 12 other AWS services in real-time, plus monitor your AWS costs with detailed breakdowns.

## Features

### 📊 **21 AWS Services Monitored**

#### 💻 Compute
- **EC2 Instances** — Track running/stopped instances with state, type, launch time, and tags
- **Lambda Functions** — Monitor runtime, memory, timeout, code size, and last modified
- **ECS Clusters** — Container orchestration with running/pending task counts and service status
- **EKS Clusters** — Kubernetes cluster monitoring with version, endpoint, and health status
- **Auto Scaling Groups** — Monitor ASG capacity, desired/min/max instances and health check type
- **Elastic Beanstalk** — Monitor environments with health (Green/Yellow/Red), status, tier, CNAME, and solution stack

#### 🗄️ Data & Storage
- **RDS Databases** — Track database instances, engine versions, class, and allocated storage
- **DynamoDB Tables** — Monitor table status, item counts, and storage size
- **ElastiCache** — Redis/Memcached/Valkey cluster monitoring with engine, node type, and node count
- **S3 Buckets** — Track buckets per region with creation dates
- **EBS Volumes** — Monitor volumes, attachment status, size, type, IOPS, AZ, and encryption

#### 🌐 Networking & Messaging
- **API Gateway** — REST, HTTP, and WebSocket API monitoring with type, endpoint, and creation date
- **Route 53** — Global DNS hosting with public/private zone monitoring, record counts, and comments
- **ALB / NLB Load Balancers** — Application and Network load balancers with DNS, scheme, state, and VPC
- **Classic Load Balancers** — Legacy ELB with registered instances, listeners, health check config, and VPC
- **EFS File Systems** — Elastic File System monitoring with state, size, mount targets, performance mode, and encryption
- **Elastic IPs** — Track allocated IPs and identify unattached (costly) IPs
- **SNS Topics** — Monitor notification topics and subscription counts
- **SQS Queues** — Track message queues with available/in-flight/delayed message counts
- **Kinesis Streams** — Monitor data streams with status, mode, shard count, retention period, and consumer count

#### 📊 Monitoring
- **CloudWatch Alarms** — Monitor alarm states (OK/ALARM/INSUFFICIENT_DATA) with metric, namespace, and reason

### 💰 **Cost Tracking**
- **Daily Costs** — Yesterday's AWS spending with full history for graphing
- **Month-to-Date Costs** — Running total for current month
- **Cost by Service** — Top 10 services ranked by spend with percentages
- **Cost Optimisation** — Configurable refresh interval (default 24 hours) to minimise Cost Explorer API charges

### 🌍 **Multi-Region Support**
- Monitor all AWS regions or select specific regions
- Global summary sensor aggregating resources across all regions
- Regional summary sensors for each monitored region
- Automatic region detection and filtering

### 📈 **Dynamic Resource Tracking**
- Sensors created dynamically as resources are discovered — no restart needed when new resources appear
- Sensors automatically removed when resources are deleted
- Historical data for trend analysis and alerting

### 🔒 **Resilient & Observable**
- Per-service boto3 timeouts (10s connect, 30s read) — no coordinator can hang indefinitely
- IAM permission errors logged once as a warning then suppressed — no log spam
- Credential errors raise a persistent HA notification
- Throttling errors logged at WARNING (transient) vs ERROR (persistent)
- Error recovery logged when a previously failing service succeeds again

### ⚙️ **Flexible Configuration**
- Configurable refresh intervals (1–1440 minutes)
- Separate Cost Explorer refresh interval (60–1440 minutes)
- Optional individual count sensors for history graphs
- Skip initial refresh option for faster HA restarts (always does full refresh on first setup)

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click **Integrations**
3. Click the three dots → **Custom repositories**
4. Add: `https://github.com/ianpleasance/home-assistant-aws-infrastructure`
5. Category: Integration
6. Search for **AWS Infrastructure Monitor** and click **Download**
7. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Copy the `custom_components/aws_infrastructure` folder to `config/custom_components/`
3. Restart Home Assistant

## Configuration

### 1. Create AWS IAM User

Create a dedicated IAM user with read-only permissions. The minimum required policy is:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "HomeAssistantAWSMonitoring",
            "Effect": "Allow",
            "Action": [
                "apigateway:GET",
                "autoscaling:DescribeAutoScalingGroups",
                "ce:GetCostAndUsage",
                "cloudwatch:DescribeAlarms",
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
                "ec2:DescribeAddresses",
                "elasticbeanstalk:DescribeEnvironments",
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
                "ec2:DescribeVolumes",
                "ecs:DescribeClusters",
                "ecs:ListClusters",
                "eks:DescribeCluster",
                "eks:ListClusters",
                "elasticache:DescribeCacheClusters",
                "elasticfilesystem:DescribeFileSystems",
                "elasticloadbalancing:DescribeLoadBalancers",
                "elasticloadbalancing:DescribeLoadBalancerAttributes",
                "kinesis:DescribeStreamSummary",
                "kinesis:ListStreams",
                "lambda:ListFunctions",
                "rds:DescribeDBInstances",
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

> **Note**: `sts:GetCallerIdentity` is used to validate credentials during setup. If your security policy prohibits this, the integration will still work — it will simply skip the validation step.

### 2. Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **AWS Infrastructure Monitor**
4. Enter your configuration:
   - **Account Name**: A friendly name (e.g., "Production", "Live")
   - **AWS Access Key ID**: Your IAM user access key
   - **AWS Secret Access Key**: Your IAM user secret key
   - **Region Mode**: "All regions" or "Select specific regions"
   - **Refresh Interval**: How often to poll AWS (default: 5 minutes)
   - **Create Individual Count Sensors**: Enable for history graphs

> **Note**: Cost data is only available via `us-east-1`. Ensure `us-east-1` is included in your monitored regions if you want cost sensors.

### 3. Configure Options (Optional)

After adding, click **Configure** to adjust:

- **Refresh Interval**: Resource polling frequency (1–1440 minutes)
- **Cost Refresh Interval**: Cost Explorer polling (60–1440 minutes, default: 1440)
  - ⚠️ Cost Explorer charges **$0.01 per API call**. Default 24h = ~$0.60/month
- **Individual Count Sensors**: Enable/disable count sensors per resource type
- **Skip Initial Refresh**: Defer first data fetch on HA **restarts** for faster startup. Has no effect when the integration is first added or reconfigured — a full refresh always runs in those cases.

## Cost Considerations

### AWS Cost Explorer API Charges

| Refresh Interval | Calls/Day | Cost/Month | Recommendation |
|------------------|-----------|------------|----------------|
| **1440 min (24h)** | 2 | **$0.60** | ✅ Recommended |
| 720 min (12h) | 4 | $1.20 | Twice-daily |
| 60 min (1h) | 48 | $14.40 | Frequent |
| 5 min | 576 | $172.80 | ❌ Not recommended |

Cost data from AWS updates once per day — more frequent polling wastes money with no benefit.

### Other AWS API Costs

All other AWS API calls used by this integration (EC2, RDS, Lambda, etc.) are **free** within normal usage limits.

## Troubleshooting

### Credential Errors

If your AWS credentials expire or are revoked, the integration will:
1. Log an ERROR with details of which account is affected
2. Raise a **persistent notification** in the HA UI
3. Continue returning the last known data for all sensors

To fix: go to **Settings → Devices & Services → AWS Infrastructure → Configure** and re-enter valid credentials, or delete and re-add the integration with new credentials.

### IAM Permission Errors

If a service returns a permission denied error (e.g. you have EC2 but not ECS in your IAM policy):
- A **WARNING** is logged once for that service
- The service shows 0/empty data
- No further log spam — the warning is suppressed on subsequent refreshes
- When the permission is granted and the next refresh succeeds, a recovery INFO message is logged

### Service Not Available in Region

Some AWS services are not available in all regions. These are handled the same way as permission errors — warned once and suppressed.

### No Data / Sensors Unavailable

1. Check **Settings → System → Logs** for `aws_infrastructure` errors
2. Verify IAM permissions include all required actions
3. Confirm the AWS region you're monitoring actually has resources
4. Try calling service `aws_infrastructure.refresh_account` manually

### Cost Data Not Updating

1. Cost data takes 24 hours to appear for new accounts
2. Ensure `ce:GetCostAndUsage` is in your IAM policy
3. Confirm Cost Explorer is enabled in your AWS account
4. Cost data only available via `us-east-1`

## Supported Languages

🇬🇧 English • 🇫🇷 French • 🇩🇪 German • 🇮🇹 Italian • 🇪🇸 Spanish • 🇳🇱 Dutch • 🇸🇪 Swedish • 🇳🇴 Norwegian • 🇩🇰 Danish • 🇵🇱 Polish • 🇵🇹 Portuguese • 🇫🇮 Finnish • 🇯🇵 Japanese

## Contributing

Contributions are welcome! Fork the repository, create a feature branch, make your changes, and submit a pull request.

## Support

- **Issues**: [GitHub Issues](https://github.com/ianpleasance/home-assistant-aws-infrastructure/issues)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

## Changelog

### v1.5.9 (2026-03-20)
- ✨ Added API Gateway monitoring (v1 REST and v2 HTTP/WebSocket) with type, endpoint type, API endpoint, and creation date

### v1.5.8 (2026-03-18)
- ✨ Added Route 53 hosted zone monitoring with public/private type, record counts, and comments (global service, fetched via us-east-1)

### v1.5.7 (2026-03-18)
- ✨ Added Elastic Beanstalk environment monitoring with health, status, tier, CNAME, and solution stack

### v1.5.6 (2026-03-18)
- ✨ Added Kinesis stream monitoring with status, mode, shard count, retention, and consumer count

### v1.5.5 (2026-03-18)
- ✨ Added EFS (Elastic File System) monitoring with state, size, mount targets, performance mode, throughput mode, and encryption status

### v1.5.4 (2026-03-18)
- ✨ Added Classic Load Balancer (ELB v1) monitoring with instance count, listeners, health check, and VPC

### v1.5.0 (2026-03-18)
- 🔒 Added botocore exception classification (credentials, permissions, throttling, timeouts, unavailable regions)
- 🔒 Credential errors now raise a persistent HA notification
- 🔒 IAM permission errors warned once then suppressed — no log spam
- 🔒 Throttling logged at WARNING not ERROR
- 🔒 Error recovery logged when a service starts succeeding again
- 🔒 Config flow credential test now has a 10s/15s timeout and meaningful error messages
- 📈 Dynamic entity registration — sensors appear as soon as coordinator data arrives, no restart needed
- 🧹 Automatic cleanup of stale entities when AWS resources are deleted
- ⚡ Concurrent first refresh via asyncio.gather — one slow service no longer blocks all others
- ⚙️ skip_initial_refresh now only applies on HA restarts, not on first setup or reconfigure
- 📋 IAM policy cleaned up — removed duplicates, only includes permissions actually used

### v1.3.0 (2026-03-10)
- ✨ Added EBS, SNS, SQS, S3, CloudWatch Alarms, Elastic IPs monitoring
- 🐛 Various bug fixes and pagination improvements
