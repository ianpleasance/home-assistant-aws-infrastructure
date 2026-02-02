# AWS Infrastructure Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A comprehensive Home Assistant integration for monitoring your AWS infrastructure across multiple regions. Track EC2 instances, Lambda functions, RDS databases, and 12 other AWS services in real-time, plus monitor your AWS costs with detailed breakdowns.

## Features

### 📊 **15 AWS Services Monitored**

#### 💻 Compute
- **EC2 Instances** - Track running/stopped instances with detailed metadata
- **Lambda Functions** - Monitor function count, runtime, memory, and execution details
- **ECS Clusters** - Container orchestration with task counts and service status
- **EKS Clusters** - Kubernetes cluster monitoring with version and health status
- **Auto Scaling Groups** - Monitor ASG capacity, desired/min/max instances

#### 🗄️ Data & Storage
- **RDS Databases** - Track database instances, engine versions, and status
- **DynamoDB Tables** - Monitor table status, item counts, and storage size
- **ElastiCache** - Redis/Memcached cluster monitoring with node details
- **S3 Buckets** - Track buckets across regions with creation dates
- **EBS Volumes** - Monitor volumes, attachment status, size, type, and IOPS

#### 🌐 Networking & Messaging
- **Load Balancers** - ALB/NLB/CLB monitoring with DNS and state
- **Elastic IPs** - Track allocated IPs and identify unattached (costly) IPs
- **SNS Topics** - Monitor notification topics and subscription counts
- **SQS Queues** - Track message queues with available/in-flight/delayed counts

#### 📊 Monitoring
- **CloudWatch Alarms** - Monitor alarm states (OK/ALARM/INSUFFICIENT_DATA)

### 💰 **Cost Tracking**
- **Daily Costs** - Yesterday's AWS spending with full history
- **Month-to-Date Costs** - Running total for current month
- **Cost by Service** - Top 10 services ranked by spend with percentages
- **Cost Optimization** - Configurable refresh interval (default 24 hours) to minimize Cost Explorer API charges

### 🌍 **Multi-Region Support**
- Monitor all AWS regions or select specific regions
- Global summary sensor aggregating resources across all regions
- Regional summary sensors for each monitored region
- Automatic region detection and filtering

### 📈 **Individual Resource Tracking**
- Create sensors for each EC2 instance, Lambda function, RDS database, etc.
- Track detailed attributes (state, tags, configuration, performance)
- Historical data for trend analysis and alerting
- Automatic entity creation and cleanup

### ⚙️ **Flexible Configuration**
- Configurable refresh intervals (1-60 minutes for resources)
- Separate Cost Explorer refresh interval (60-1440 minutes)
- Optional individual count sensors for history graphs
- Skip initial refresh option for faster startup
- Easy account management via UI

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/ianpleasance/home-assistant-aws-infrastructure`
6. Category: Integration
7. Click "Add"
8. Search for "AWS Infrastructure Monitor"
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Copy the `custom_components/aws_infrastructure` folder to your Home Assistant `config/custom_components/` directory
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
        "rds:DescribeDBClusters",
        "lambda:ListFunctions",
        "elasticloadbalancing:DescribeLoadBalancers",
        "autoscaling:DescribeAutoScalingGroups",
        "dynamodb:ListTables",
        "dynamodb:DescribeTable",
        "elasticache:DescribeCacheClusters",
        "elasticache:DescribeReplicationGroups",
        "ecs:ListClusters",
        "ecs:DescribeClusters",
        "ecs:ListServices",
        "ecs:DescribeServices",
        "ecs:ListTasks",
        "ecs:DescribeTasks",
        "eks:ListClusters",
        "eks:DescribeCluster",
        "sns:ListTopics",
        "sns:GetTopicAttributes",
        "sqs:ListQueues",
        "sqs:GetQueueAttributes",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "s3:GetBucketTagging",
        "cloudwatch:DescribeAlarms",
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
3. Search for "AWS Infrastructure Monitor"
4. Enter your configuration:
   - **Account Name**: A friendly name (e.g., "Production", "Live")
   - **AWS Access Key ID**: Your IAM user access key
   - **AWS Secret Access Key**: Your IAM user secret key
   - **Region Mode**: "All regions" or "Select specific regions"
   - **Refresh Interval**: How often to check AWS (5-60 minutes, default: 5)
   - **Create Individual Count Sensors**: Enable for history graphs

### 3. Configure Options (Optional)

After adding the integration, click **Configure** to adjust:

- **Refresh Interval**: Resource polling frequency (1-60 minutes)
- **Cost Refresh Interval**: Cost Explorer polling frequency (60-1440 minutes, default: 1440)
  - ⚠️ **Important**: Cost Explorer charges **$0.01 per API call**. Default is 24 hours (2 calls/day = $0.60/month)
- **Individual Count Sensors**: Enable/disable count sensors per resource type
- **Skip Initial Refresh**: Speed up startup by deferring first data fetch

## Cost Considerations

### AWS Cost Explorer API Charges

AWS charges **$0.01 per API request** to Cost Explorer after the first request each day.

| Refresh Interval | Calls/Day | Cost/Month | Recommended For |
|------------------|-----------|------------|-----------------|
| **1440 min (24h)** | 2 | **$0.60** | ✅ **Recommended** - Cost data updates daily |
| 720 min (12h) | 4 | $1.20 | Twice-daily updates |
| 120 min (2h) | 24 | $7.20 | Frequent monitoring |
| 60 min (1h) | 48 | $14.40 | Real-time tracking |
| 5 min | 576 | $172.80 | ❌ **Not recommended** |

**Default**: 1440 minutes (24 hours) = **$0.60/month**

Cost data from AWS only updates once per day, so checking more frequently provides no benefit and wastes money.

### Other AWS API Costs

Most other AWS API calls (EC2, RDS, Lambda, etc.) are **free** within normal usage limits.

## Sensors Created

### Global Sensors

- `sensor.aws_{account}_global_summary` - Total resource count across all regions
- `sensor.aws_{account}_global_cost_yesterday` - Yesterday's total cost
- `sensor.aws_{account}_global_cost_month_to_date` - Month-to-date cost
- `sensor.aws_{account}_global_cost_service_{service}` - Top 10 services by cost

### Regional Sensors

- `sensor.aws_{account}_{region}_summary` - Resource count per region
- `sensor.aws_{account}_{region}_ec2_count` - EC2 instance count (optional)
- `sensor.aws_{account}_{region}_rds_count` - RDS database count (optional)
- `sensor.aws_{account}_{region}_lambda_count` - Lambda function count (optional)
- *(And 10 more count sensors for other services)*

### Individual Resource Sensors

- `sensor.aws_{account}_{region}_ec2_i_{instance_id}` - Per EC2 instance
- `sensor.aws_{account}_{region}_rds_{db_identifier}` - Per RDS database
- `sensor.aws_{account}_{region}_lambda_{function_name}` - Per Lambda function
- *(And individual sensors for all 15 service types)*

## Services

### `aws_infrastructure.refresh_account`

Manually refresh all AWS data for an account.

```yaml
service: aws_infrastructure.refresh_account
data:
  account_name: "live"
```

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

### Monthly Budget Warning

```yaml
automation:
  - alias: "AWS Monthly Budget Warning"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.aws_live_global_cost_month_to_date
        above: 100
    action:
      - service: notify.mobile_app
        data:
          title: "AWS Budget Warning"
          message: "Month-to-date AWS cost is ${{ states('sensor.aws_live_global_cost_month_to_date') }}"
```

### Unattached Elastic IP Alert

```yaml
automation:
  - alias: "AWS Unattached Elastic IP Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.aws_live_global_summary
        value_template: "{{ state.attributes.elastic_ips_unattached }}"
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "AWS Cost Optimization"
          message: "You have {{ state_attr('sensor.aws_live_global_summary', 'elastic_ips_unattached') }} unattached Elastic IPs costing money"
```

### EC2 Instance State Change

```yaml
automation:
  - alias: "EC2 Instance State Change"
    trigger:
      - platform: state
        entity_id: sensor.aws_live_us_east_1_ec2_i_12345abcde
    action:
      - service: notify.mobile_app
        data:
          title: "EC2 State Change"
          message: "Instance {{ trigger.to_state.attributes.instance_id }} changed from {{ trigger.from_state.state }} to {{ trigger.to_state.state }}"
```

## Dashboard Examples

See the [examples](examples/) folder for:
- Simple overview dashboard
- Detailed multi-tab dashboard
- Cost tracking dashboard
- Per-service dashboards

## Supported Languages

This integration includes translations for:

🇬🇧 English • 🇫🇷 French • 🇩🇪 German • 🇮🇹 Italian • 🇪🇸 Spanish • 🇳🇱 Dutch • 🇸🇪 Swedish • 🇳🇴 Norwegian • 🇩🇰 Danish • 🇵🇱 Polish • 🇵🇹 Portuguese • 🇫🇮 Finnish • 🇯🇵 Japanese • 🇰🇷 Korean

## Troubleshooting

### Authentication Errors

**Error**: `Caught blocking call to putrequest inside the event loop`
**Solution**: Update to the latest version - this was fixed in v0.4.0

**Error**: `Authentication failed`
**Solution**: 
- Verify your AWS Access Key ID and Secret Access Key
- Ensure the IAM user has the required permissions
- Check if the access key is active in AWS IAM console

### No Data Showing

**Problem**: Sensors show "unknown" or "unavailable"
**Solutions**:
1. Check Home Assistant logs for errors
2. Verify IAM permissions include all required actions
3. Ensure refresh interval hasn't been set too high
4. Try manually refreshing: `aws_infrastructure.refresh_account`

### Cost Data Not Updating

**Problem**: Cost sensors show "unknown"
**Solutions**:
1. Cost data takes 24 hours to appear for new accounts
2. Verify IAM policy includes `ce:GetCostAndUsage` permission
3. Check that Cost Explorer is enabled in your AWS account
4. Cost data only available in `us-east-1` region

### High AWS Costs

**Problem**: Unexpected AWS Cost Explorer charges
**Solution**: Check your Cost Refresh Interval in integration options. Default is 24 hours ($0.60/month). If set to 5 minutes, you'll be charged $172.80/month!

## Performance

- **Startup Time**: 30-60 seconds (depends on number of resources)
- **Memory Usage**: ~50-100MB (depends on number of regions/resources)
- **Database Growth**: ~10-20MB per month (depends on refresh frequency)

## Limitations

- Cost data only available in `us-east-1` region (AWS limitation)
- Cost data has 24-hour delay (AWS limitation)
- Some AWS services not yet supported (CloudFront, Route53 hosted zones, etc.)
- Maximum 20 regions can be monitored simultaneously
- Individual resource sensors created for each resource (can be hundreds of entities)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/ianpleasance/home-assistant-aws-infrastructure/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ianpleasance/home-assistant-aws-infrastructure/discussions)
- **Home Assistant Community**: [Community Forum Thread](https://community.home-assistant.io/)

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details

## Credits

Created by [Your Name]

Built with:
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) - AWS SDK for Python
- [Home Assistant](https://www.home-assistant.io/) - Open source home automation

## Changelog

### v1.0.0 (2026-02-02)
- ✨ Added 10 new AWS services (DynamoDB, ElastiCache, ECS, EKS, EBS, SNS, SQS, S3, CloudWatch Alarms, Elastic IPs)
- ✨ Added configurable Cost Explorer refresh interval
- 🐛 Fixed blocking boto3 calls in async context
- 🐛 Fixed Cost Explorer GroupBy syntax
- 🌍 Added 13 language translations
- 📊 Enhanced dashboards with all new services
- 💰 Cost optimization features (default 24h refresh = $0.60/month)

### v0.3.4 (2026-01-29)
- 🐛 Fixed domain rename cleanup issues
- 🐛 Fixed cost sensor calculations

### v0.3.0 (2026-01-28)
- ✨ Added Load Balancer monitoring
- ✨ Added Auto Scaling Group monitoring
- 🐛 Fixed multi-region support

### v0.2.0 (2026-01-27)
- ✨ Added cost tracking with Cost Explorer
- ✨ Added service cost breakdown

### v0.1.0 (2026-01-26)
- 🎉 Initial release
- ✨ EC2, RDS, Lambda monitoring
- ✨ Multi-region support

## Roadmap

- [ ] Cost forecasting and alerts
- [ ] Resource tagging insights
- [ ] Multi-account support
- [ ] CloudWatch metrics integration

---

**⭐ If you find this integration useful, please star the repository!**

