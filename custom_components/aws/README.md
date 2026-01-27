# AWS Infrastructure Monitor for Home Assistant

**Version:** 0.1.0  
**Author:** Ian Pleasance ([@ianpleasance](https://github.com/ianpleasance))  
**Email:** ianpleasance@gmail.com

Monitor your AWS infrastructure directly from Home Assistant! Track costs, EC2 instances, RDS databases, Lambda functions, Load Balancers, and Auto Scaling Groups across multiple regions.

## Features

✅ **Multi-Region Support** - Monitor all AWS regions or select specific ones  
✅ **Cost Tracking** - Daily and month-to-date costs with service breakdowns  
✅ **EC2 Monitoring** - Instance states, types, IPs, and attached volumes  
✅ **RDS Databases** - Status, engine, storage, and endpoint information  
✅ **Lambda Functions** - Runtime, state, memory, timeout configuration  
✅ **Load Balancers** - ALB/NLB/CLB state, DNS, and availability zones  
✅ **Auto Scaling Groups** - Capacity, health, and instance counts  
✅ **Configurable Refresh** - Set update intervals from 1-1440 minutes  
✅ **Manual Refresh Services** - Force updates on-demand

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right
4. Select "Custom repositories"
5. Add: `https://github.com/ianpleasance/aws_infrastructure`
6. Category: Integration
7. Click "Add"
8. Search for "AWS Infrastructure Monitor"
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/aws_infrastructure` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Wait 1-2 minutes for Home Assistant to install boto3 and botocore dependencies

## Configuration

### Via UI (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "AWS Infrastructure Monitor"
4. Enter your configuration:
   - **Account Name**: Friendly name (e.g., "production", "dev")
   - **AWS Access Key ID**: Your AWS access key
   - **AWS Secret Access Key**: Your AWS secret key
   - **Region Mode**: 
     - "Monitor all AWS regions" - Automatically discovers and monitors all enabled regions
     - "Select specific regions" - Choose which regions to monitor
   - **Refresh Interval**: How often to update data (1-1440 minutes, default: 5)

### AWS Credentials Setup

**Recommended:** Create an IAM user with read-only permissions:

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
        "lambda:Get*",
        "elasticloadbalancing:Describe*",
        "autoscaling:Describe*",
        "ce:GetCostAndUsage",
        "cloudwatch:GetMetricStatistics"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note:** Cost Explorer (`ce:GetCostAndUsage`) only works in `us-east-1` region.

## Entity Examples

Entities are created with the following naming pattern:
```
sensor.aws_{account_name}_{region}_{resource}_{metric}
```

### Cost Sensors
```
sensor.aws_production_us_east_1_cost_today
sensor.aws_production_us_east_1_cost_mtd
```

### EC2 Sensors
```
sensor.aws_production_us_east_1_ec2_instances_running
sensor.aws_production_us_east_1_ec2_instances_stopped
sensor.aws_production_us_east_1_ec2_i_1234567890abcdef0_state
```

### RDS Sensors
```
sensor.aws_production_us_east_1_rds_total_instances
sensor.aws_production_us_east_1_rds_mydb_status
```

### Lambda Sensors
```
sensor.aws_production_us_east_1_lambda_total_functions
sensor.aws_production_us_east_1_lambda_my_function_state
```

### Load Balancer Sensors
```
sensor.aws_production_us_east_1_lb_my_alb_state
```

### Auto Scaling Sensors
```
sensor.aws_production_us_east_1_asg_my_asg_instances
```

## Services

### `aws_infrastructure.refresh_account`

Force refresh all data for a specific account.

```yaml
service: aws_infrastructure.refresh_account
data:
  account_name: production
```

Refresh a specific region only:

```yaml
service: aws_infrastructure.refresh_account
data:
  account_name: production
  region: us-east-1
```

### `aws_infrastructure.refresh_all_accounts`

Force refresh all configured accounts and regions.

```yaml
service: aws_infrastructure.refresh_all_accounts
```

## Automation Examples

### Daily Cost Alert

```yaml
automation:
  - alias: AWS Daily Cost Alert
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: notify.mobile_app
        data:
          title: "AWS Costs"
          message: >
            Yesterday: ${{ states('sensor.aws_production_us_east_1_cost_today') }}
            Month to date: ${{ states('sensor.aws_production_us_east_1_cost_mtd') }}
```

### EC2 Instance State Change

```yaml
automation:
  - alias: EC2 Instance Stopped
    trigger:
      - platform: state
        entity_id: sensor.aws_production_us_east_1_ec2_i_1234567890abcdef0_state
        to: "stopped"
    action:
      - service: notify.slack
        data:
          message: "Production EC2 instance has stopped!"
```

### Cost Spike Detection

```yaml
automation:
  - alias: AWS Cost Spike
    trigger:
      - platform: numeric_state
        entity_id: sensor.aws_production_us_east_1_cost_today
        above: 100
    action:
      - service: notify.email
        data:
          title: "AWS Cost Alert"
          message: "Daily cost exceeded $100: ${{ states('sensor.aws_production_us_east_1_cost_today') }}"
```

## Dashboard Example

```yaml
type: vertical-stack
cards:
  - type: entities
    title: AWS Production - Costs
    entities:
      - entity: sensor.aws_production_us_east_1_cost_today
        name: "Today"
      - entity: sensor.aws_production_us_east_1_cost_mtd
        name: "Month to Date"

  - type: entities
    title: AWS Production - Infrastructure
    entities:
      - entity: sensor.aws_production_us_east_1_ec2_instances_running
        name: "EC2 Running"
      - entity: sensor.aws_production_us_east_1_rds_total_instances
        name: "RDS Databases"
      - entity: sensor.aws_production_us_east_1_lambda_total_functions
        name: "Lambda Functions"
```

## Troubleshooting

### Integration Not Loading

1. Check Home Assistant logs for errors
2. Verify boto3 installation completed (may take 30-60 seconds on first load)
3. Ensure AWS credentials are correct
4. Check IAM permissions include all required actions

### No Cost Data

- Cost Explorer is only available in `us-east-1` region
- Ensure the IAM user has `ce:GetCostAndUsage` permission
- Cost data may take 24 hours to appear for the first time

### Regions Not Discovered

If "Monitor all regions" doesn't find all regions:
- Check IAM user has `ec2:DescribeRegions` permission
- Verify regions are enabled in your AWS account
- Integration falls back to common regions if discovery fails

### Performance Issues

If experiencing slow updates:
- Increase refresh interval in integration options
- Consider selecting specific regions instead of monitoring all
- Use manual refresh services for on-demand updates

## Recommended Refresh Intervals

| Service | Recommended Interval | Rationale |
|---------|---------------------|-----------|
| Cost Tracking | 360 min (6 hours) | Updates once daily |
| RDS | 5-10 min | Important for monitoring |
| Lambda | 1-5 min | High-volume metrics |
| Load Balancers | 2-5 min | Health checks time-sensitive |
| Auto Scaling | 2-5 min | Scaling events need detection |
| EC2 | 5-10 min | Instance state changes |

Lower intervals = more API calls = potential AWS charges for high-volume use.

## Changelog

### Version 0.1.0 (2026-01-17)

- Initial release
- Multi-region support with auto-discovery
- Cost tracking (daily and MTD)
- EC2 instance monitoring
- RDS database monitoring
- Lambda function tracking
- Load Balancer (ALB/NLB/CLB) support
- Auto Scaling Group monitoring
- Configurable refresh intervals
- Manual refresh services

## Support

- **Issues**: [GitHub Issues](https://github.com/ianpleasance/aws_infrastructure/issues)
- **Email**: ianpleasance@gmail.com
- **Home Assistant Community**: Tag @ianpleasance

## License

MIT License - See LICENSE file for details

## Credits

Developed by Ian Pleasance with assistance from Claude (Anthropic).

## Contributing

Contributions welcome! Please submit pull requests or open issues on GitHub.
