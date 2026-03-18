# AWS Infrastructure Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A comprehensive Home Assistant integration for monitoring your AWS infrastructure across multiple regions. Track EC2 instances, Lambda functions, RDS databases, and 21 other AWS services in real-time, plus monitor your AWS costs with detailed breakdowns.

## Features

### 📊 **23 AWS Services Monitored**

#### 💻 Compute
- **EC2 Instances** — Track running/stopped instances with state, type, launch time, and tags
- **Lambda Functions** — Monitor runtime, memory, timeout, code size, and last modified
- **ECS Clusters** — Container orchestration with running/pending task counts and service status
- **EKS Clusters** — Kubernetes cluster monitoring with version, endpoint, and health status
- **Auto Scaling Groups** — Monitor ASG capacity, desired/min/max instances and health check type
- **Elastic Beanstalk** — Application environments with health (Green/Yellow/Red), status, tier, CNAME, and endpoint

#### 🗄️ Data & Storage
- **RDS Databases** — Track database instances, engine versions, class, and allocated storage
- **DynamoDB Tables** — Monitor table status, item counts, and storage size
- **ElastiCache** — Redis/Memcached/Valkey cluster monitoring with engine, node type, and node count
- **S3 Buckets** — Track buckets per region with creation dates
- **EBS Volumes** — Monitor volumes, attachment status, size, type, IOPS, AZ, and encryption
- **EFS File Systems** — Elastic file systems with lifecycle state, size, mount targets, performance mode, and throughput mode

#### 🌐 Networking & Messaging
- **ALB / NLB Load Balancers** — Application and Network load balancers with DNS, scheme, state, and VPC
- **Classic Load Balancers** — Legacy ELB detection with registered instances, listeners, health check config
- **Elastic IPs** — Track allocated IPs and identify unattached (costly) IPs
- **SNS Topics** — Monitor notification topics and subscription counts
- **SQS Queues** — Track message queues with available/in-flight/delayed message counts
- **Kinesis Streams** — Data streams with status, mode (provisioned/on-demand), shard count, retention, and consumer count

#### 🔌 APIs & CDN
- **API Gateway** — Both REST APIs (v1) and HTTP/WebSocket APIs (v2) in a single view
- **CloudFront** — Global CDN distributions with status, domain, origins, aliases, price class, and HTTP version
- **Route 53** — Global hosted zones (public and private) with record counts

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
- CloudFront and Route 53 are global services — fetched once via us-east-1 regardless of region selection
- Automatic region detection and filtering

### 📈 **Individual Resource Tracking**
- Create sensors for each EC2 instance, Lambda function, RDS database, load balancer, etc.
- Track detailed attributes (state, tags, configuration, endpoints)
- Historical data for trend analysis and alerting
- Automatic entity creation and cleanup when resources change

### ⚙️ **Flexible Configuration**
- Configurable refresh intervals (1–1440 minutes)
- Separate Cost Explorer refresh interval (60–1440 minutes)
- Optional individual count sensors for history graphs
- Skip initial refresh option for faster startup

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

Create a dedicated IAM user with the following policy:

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

> **Note**: Cost usage data is only available via us-east-1. If you want cost sensors, ensure us-east-1 is included in your monitored regions even if you have no other resources there. CloudFront and Route 53 are also always fetched via us-east-1 regardless of region selection as they are global services.

### 3. Configure Options (Optional)

After adding the integration, click **Configure** to adjust:

- **Refresh Interval**: Resource polling frequency (1–1440 minutes)
- **Cost Refresh Interval**: Cost Explorer polling (60–1440 minutes, default: 1440)
  - ⚠️ Cost Explorer charges **$0.01 per API call**. Default 24h = ~$0.60/month
- **Individual Count Sensors**: Enable/disable count sensors per resource type
- **Skip Initial Refresh**: Defer first data fetch for faster startup

## Cost Considerations

### AWS Cost Explorer API Charges

| Refresh Interval | Calls/Day | Cost/Month | Recommendation |
|------------------|-----------|------------|----------------|
| **1440 min (24h)** | 2 | **$0.60** | ✅ Recommended |
| 720 min (12h) | 4 | $1.20 | Twice-daily |
| 60 min (1h) | 48 | $14.40 | Frequent |
| 5 min | 576 | $172.80 | ❌ Not recommended |

Cost data from AWS only updates once per day — more frequent polling wastes money with no benefit.

### Other AWS API Costs

Most AWS API calls (EC2, RDS, Lambda, EFS, Kinesis, Beanstalk, etc.) are **free** within normal usage limits. API Gateway management API calls and Route 53 `ListHostedZones` calls are also free tier.

## Sensors Created

### Global Sensors (account-wide)

| Sensor | Description |
|--------|-------------|
| `sensor.aws_{account}_global_summary` | Total resource count across all regions |
| `sensor.aws_{account}_global_cost_yesterday` | Yesterday's total cost (USD) |
| `sensor.aws_{account}_global_cost_month_to_date` | Month-to-date cost (USD) |
| `sensor.aws_{account}_global_cost_service_{service}` | Top 10 services by cost |
| `sensor.aws_{account}_global_cloudfront_{id}` | Per CloudFront distribution |
| `sensor.aws_{account}_global_route53_{id}` | Per Route 53 hosted zone |

### Regional Sensors (per region)

| Sensor | Description |
|--------|-------------|
| `sensor.aws_{account}_{region}_summary` | Resource count for this region |
| `sensor.aws_{account}_{region}_ec2_i_{id}` | Per EC2 instance |
| `sensor.aws_{account}_{region}_rds_{id}` | Per RDS database |
| `sensor.aws_{account}_{region}_lambda_{name}` | Per Lambda function |
| `sensor.aws_{account}_{region}_lb_{name}` | Per ALB/NLB load balancer |
| `sensor.aws_{account}_{region}_classic_lb_{name}` | Per Classic load balancer |
| `sensor.aws_{account}_{region}_asg_{name}` | Per Auto Scaling Group |
| `sensor.aws_{account}_{region}_dynamodb_{name}` | Per DynamoDB table |
| `sensor.aws_{account}_{region}_elasticache_{id}` | Per ElastiCache cluster |
| `sensor.aws_{account}_{region}_ecs_{name}` | Per ECS cluster |
| `sensor.aws_{account}_{region}_eks_{name}` | Per EKS cluster |
| `sensor.aws_{account}_{region}_ebs_{id}` | Per EBS volume |
| `sensor.aws_{account}_{region}_efs_{id}` | Per EFS file system |
| `sensor.aws_{account}_{region}_sns_{name}` | Per SNS topic |
| `sensor.aws_{account}_{region}_sqs_{name}` | Per SQS queue |
| `sensor.aws_{account}_{region}_s3_{name}` | Per S3 bucket |
| `sensor.aws_{account}_{region}_alarm_{name}` | Per CloudWatch alarm |
| `sensor.aws_{account}_{region}_eip_{ip}` | Per Elastic IP |
| `sensor.aws_{account}_{region}_apigw_{id}` | Per API Gateway |
| `sensor.aws_{account}_{region}_kinesis_{name}` | Per Kinesis stream |
| `sensor.aws_{account}_{region}_beanstalk_{name}` | Per Beanstalk environment |

Optional count sensors (enabled via "Create Individual Count Sensors"):
`ec2_count`, `rds_count`, `lambda_count`, `classic_lb_count`, `dynamodb_count`, `elasticache_count`, `ecs_count`, `eks_count`, `ebs_count`, `efs_count`, `sns_count`, `sqs_count`, `s3_count`, `cloudwatch_alarms_count`, `elastic_ips_count`, `api_gateway_count`, `kinesis_count`, `beanstalk_count`, `cloudfront_count`, `route53_count`

## Dashboard

Two ready-made dashboards are included in the `dashboards/` folder:

- **DASHBOARD_detailed.yaml** — Full multi-tab dashboard with a tab per service group:
  - Overview, EC2, Lambda, RDS, DynamoDB, ElastiCache, Containers (ECS+EKS), Storage (S3+EBS+EFS), Messaging (SNS+SQS+Kinesis), Networking (ALB/NLB+Classic LB+EIPs), API & CDN (API Gateway+CloudFront+Route 53), Beanstalk, ASG, Monitoring, Costs
- **DASHBOARD_simple.yaml** — Single-page summary overview

To use: copy the YAML content and paste into a new dashboard via **Edit Dashboard** → **Raw configuration editor**.

## Example Automations

### Daily Cost Alert

```yaml
automation:
  - alias: "AWS Daily Cost Alert"
    trigger:
      - platform: state
        entity_id: sensor.aws_live_global_cost_yesterday
    condition:
      - condition: numeric_state
        entity_id: sensor.aws_live_global_cost_yesterday
        above: 10
    action:
      - service: notify.mobile_app
        data:
          title: "AWS Cost Alert"
          message: "Yesterday's AWS cost was ${{ states('sensor.aws_live_global_cost_yesterday') }}"
```

### Beanstalk Health Alert

```yaml
automation:
  - alias: "Beanstalk Environment Unhealthy"
    trigger:
      - platform: state
        entity_id: sensor.aws_live_eu_west_1_beanstalk_myapp_prod
        to: "Red"
    action:
      - service: notify.mobile_app
        data:
          title: "Beanstalk Alert"
          message: "Environment {{ trigger.to_state.attributes.environment_name }} is Red"
```

### Unattached Elastic IP Alert

```yaml
automation:
  - alias: "AWS Unattached Elastic IP Alert"
    trigger:
      - platform: template
        value_template: "{{ state_attr('sensor.aws_live_global_summary', 'elastic_ips_unattached') | int > 0 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "AWS Cost Optimisation"
          message: "{{ state_attr('sensor.aws_live_global_summary', 'elastic_ips_unattached') }} unattached Elastic IPs are costing money"
```

### CloudWatch Alarm Firing

```yaml
automation:
  - alias: "CloudWatch Alarm Firing"
    trigger:
      - platform: state
        entity_id: sensor.aws_live_eu_west_1_alarm_cpu_usage_75
        to: "ALARM"
    action:
      - service: notify.mobile_app
        data:
          title: "AWS CloudWatch Alert"
          message: "Alarm {{ trigger.to_state.attributes.alarm_name }} is firing: {{ trigger.to_state.attributes.reason }}"
```

## Supported Languages

🇬🇧 English • 🇫🇷 French • 🇩🇪 German • 🇮🇹 Italian • 🇪🇸 Spanish • 🇳🇱 Dutch • 🇸🇪 Swedish • 🇳🇴 Norwegian • 🇩🇰 Danish • 🇵🇱 Polish • 🇵🇹 Portuguese • 🇫🇮 Finnish • 🇯🇵 Japanese

## Troubleshooting

### No Data Showing

1. Check Home Assistant logs for errors from `aws_infrastructure`
2. Verify IAM permissions include all required actions listed above
3. Try manually refreshing: call service `aws_infrastructure.refresh_account`

### Cost Data Not Updating

1. Cost data takes 24 hours to appear for new accounts
2. Ensure `ce:GetCostAndUsage` is in your IAM policy
3. Confirm Cost Explorer is enabled in your AWS account
4. Cost data only available via `us-east-1`

### Classic Load Balancers Not Appearing

Ensure your IAM policy includes `elasticloadbalancing:DescribeLoadBalancers` (this covers both classic and v2). Classic ELBs use the same IAM namespace as ALB/NLB.

### CloudFront / Route 53 Not Appearing

These are global services fetched via `us-east-1` only. Ensure `us-east-1` is in your monitored regions. Verify IAM permissions include `cloudfront:ListDistributions` and `route53:ListHostedZones`.

### High AWS Costs

Check your Cost Refresh Interval in integration options. Default is 24 hours ($0.60/month). If set to 5 minutes you'll be charged ~$172/month.

## Limitations

- Cost data only available in `us-east-1` (AWS limitation)
- Cost data has 24-hour delay (AWS limitation)
- CloudFront and Route 53 are fetched via us-east-1 only (global services)
- Individual resource sensors are created per resource — large accounts may have hundreds of entities

## Contributing

Contributions are welcome! Fork the repository, create a feature branch, make your changes, and submit a pull request.

## Support

- **Issues**: [GitHub Issues](https://github.com/ianpleasance/home-assistant-aws-infrastructure/issues)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

## Changelog

### v1.4.0 (2026-03-18)
- ✨ Added Classic Load Balancer (ELB v1) detection and monitoring
- ✨ Added API Gateway (REST v1 + HTTP/WebSocket v2)
- ✨ Added CloudFront distribution monitoring (global)
- ✨ Added EFS file system monitoring
- ✨ Added Route 53 hosted zone monitoring (global)
- ✨ Added Kinesis data stream monitoring
- ✨ Added Elastic Beanstalk environment monitoring
- 📊 Updated detailed dashboard with new tabs: API & CDN, Beanstalk, EFS (in Storage tab), Kinesis (in Messaging tab), Classic LBs (in Networking tab)
- 📖 Updated README with all new services, IAM policy, and sensor reference

### v1.3.0 (2026-03-10)
- ✨ Added EBS volume monitoring
- ✨ Added SNS topic monitoring
- ✨ Added SQS queue monitoring
- ✨ Added S3 bucket monitoring
- ✨ Added CloudWatch alarm monitoring
- ✨ Added Elastic IP monitoring
- ✨ Various bug fixes and pagination improvements

### v1.0.0 (2026-02-02)
- ✨ Initial release with EC2, RDS, Lambda, ECS, EKS, DynamoDB, ElastiCache, ALB/NLB, ASG
- ✨ Cost Explorer integration
- 🌍 13 language translations

---

**⭐ If you find this integration useful, please star the repository!**
