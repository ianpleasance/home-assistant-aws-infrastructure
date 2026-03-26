# AWS Infrastructure Monitor — IAM Policy Reference

This document provides the IAM permissions required to use the AWS Infrastructure Monitor integration.

All permissions are **read-only**. The integration never creates, modifies, or deletes any AWS resources.

---

## Always Required

Regardless of which services you select, this permission is always needed to validate credentials:

```json
"sts:GetCallerIdentity"
```

---

## Complete Policy (All Services)

Use this if you want to monitor all 28 supported services:

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

> ⚠️ **Cost Explorer note:** AWS charges **$0.01 per API call** to Cost Explorer. With the default 24-hour refresh interval this costs approximately $0.60/month. If you do not need cost tracking, remove `ce:GetCostAndUsage` from the policy and deselect **Cost Explorer** during integration setup.

---

## Per-Service Permissions

If you only want to monitor specific services, use the minimum permissions below. Always include `sts:GetCallerIdentity` in addition to the service-specific permissions.


### Compute

<details>
<summary><b>EC2 Instances</b></summary>

```json
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
```

</details>

<details>
<summary><b>Lambda Functions</b></summary>

```json
                "lambda:ListFunctions",
```

</details>

<details>
<summary><b>Auto Scaling Groups</b></summary>

```json
                "autoscaling:DescribeAutoScalingGroups",
```

</details>

<details>
<summary><b>ECS Clusters</b></summary>

```json
                "ecs:DescribeClusters",
                "ecs:ListClusters",
```

</details>

<details>
<summary><b>EKS Clusters</b></summary>

```json
                "eks:DescribeCluster",
                "eks:ListClusters",
```

</details>

<details>
<summary><b>Elastic Beanstalk</b></summary>

```json
                "elasticbeanstalk:DescribeEnvironments",
```

</details>


### Databases & Storage

<details>
<summary><b>RDS Databases</b></summary>

```json
                "rds:DescribeDBInstances",
```

</details>

<details>
<summary><b>Redshift</b></summary>

```json
                "redshift:DescribeClusters",
```

</details>

<details>
<summary><b>DynamoDB</b></summary>

```json
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
```

</details>

<details>
<summary><b>ElastiCache</b></summary>

```json
                "elasticache:DescribeCacheClusters",
```

</details>

<details>
<summary><b>S3 Buckets</b></summary>

```json
                "s3:GetBucketLocation",
                "s3:ListAllMyBuckets",
```

</details>

<details>
<summary><b>EBS Volumes</b></summary>

```json
                "ec2:DescribeVolumes",
```

</details>

<details>
<summary><b>EFS File Systems</b></summary>

```json
                "elasticfilesystem:DescribeFileSystems",
```

</details>

<details>
<summary><b>ECR Repositories</b></summary>

```json
                "ecr:DescribeImages",
                "ecr:DescribeRepositories",
```

</details>


### Networking

<details>
<summary><b>VPC</b></summary>

```json
                "ec2:DescribeInternetGateways",
                "ec2:DescribeNatGateways",
                "ec2:DescribeSubnets",
                "ec2:DescribeVpcPeeringConnections",
                "ec2:DescribeVpcs",
                "ec2:DescribeVpnConnections",
```

</details>

<details>
<summary><b>ALB / NLB Load Balancers</b></summary>

```json
                "elasticloadbalancing:DescribeLoadBalancers",
```

</details>

<details>
<summary><b>Classic Load Balancers</b></summary>

```json
                "elasticloadbalancing:DescribeLoadBalancers",
```

</details>

<details>
<summary><b>Elastic IPs</b></summary>

```json
                "ec2:DescribeAddresses",
```

</details>

<details>
<summary><b>API Gateway</b></summary>

```json
                "apigateway:GET",
```

</details>

<details>
<summary><b>CloudFront (global)</b></summary>

```json
                "cloudfront:ListDistributions",
```

</details>

<details>
<summary><b>Route 53 (global)</b></summary>

```json
                "route53:ListHostedZones",
```

</details>


### Messaging & Streaming

<details>
<summary><b>SNS Topics</b></summary>

```json
                "sns:GetTopicAttributes",
                "sns:ListTopics",
```

</details>

<details>
<summary><b>SQS Queues</b></summary>

```json
                "sqs:GetQueueAttributes",
                "sqs:ListQueues",
```

</details>

<details>
<summary><b>Kinesis Streams</b></summary>

```json
                "kinesis:DescribeStreamSummary",
                "kinesis:ListStreams",
```

</details>


### Security & Compliance

<details>
<summary><b>IAM (global)</b></summary>

```json
                "iam:GenerateCredentialReport",
                "iam:GetAccountPasswordPolicy",
                "iam:GetAccountSummary",
                "iam:GetCredentialReport",
                "iam:ListRoles",
```

</details>

<details>
<summary><b>ACM Certificates</b></summary>

```json
                "acm:DescribeCertificate",
                "acm:ListCertificates",
```

</details>

<details>
<summary><b>CloudTrail</b></summary>

```json
                "cloudtrail:DescribeTrails",
                "cloudtrail:GetEventSelectors",
                "cloudtrail:GetTrailStatus",
```

</details>


### Monitoring & Cost

<details>
<summary><b>CloudWatch Alarms</b></summary>

```json
                "cloudwatch:DescribeAlarms",
```

</details>

<details>
<summary><b>Cost Explorer (global)</b></summary>

```json
                "ce:GetCostAndUsage",
```

</details>


---

## Recommended IAM Setup

1. Create a dedicated IAM user named e.g. `home-assistant-monitor`
2. Select **Programmatic access only** — no console access needed
3. Attach an inline policy using only the permissions for your selected services
4. Store the Access Key ID and Secret Access Key securely

Never use your root account or an administrator-level user for this integration.
