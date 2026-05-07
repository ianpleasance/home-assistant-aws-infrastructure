# AWS Infrastructure Monitor — Sensor Reference

This document lists every sensor created by the integration, its native value, and all attributes with their meanings.

---

## Naming Convention

Regional sensors follow the pattern:
```
sensor.aws_{account}_{region}__{resource_id}
```
Global sensors (IAM, CloudFront, Route 53, Cost Explorer):
```
sensor.aws_{account}_global_{resource_id}
```

---

## Compute

### EC2 Instances
**Entity ID:** `sensor.aws_{account}_{region}_ec2_i_{instance_id}`
**Native value:** Instance state (`running`, `stopped`, `terminated`, etc.)

| Attribute | Description |
|-----------|-------------|
| `instance_id` | EC2 instance ID (e.g. `i-0abc123`) |
| `instance_type` | Hardware type (e.g. `t3.micro`) |
| `state` | Current instance state |
| `launch_time` | When the instance was launched |
| `name` | Value of the `Name` tag |
| `public_ip` | Public IPv4 address, if assigned |
| `private_ip` | Private IPv4 address within the VPC |
| `public_dns` | Public DNS hostname, if assigned |
| `vpc_id` | VPC the instance belongs to |
| `subnet_id` | Subnet the instance is deployed in |
| `security_groups` | List of security group names attached |
| `key_name` | EC2 key pair name used for SSH access |
| `platform` | OS platform (`linux` or `windows`) |
| `architecture` | CPU architecture (`x86_64`, `arm64`) |
| `iam_profile` | IAM instance profile name, if attached |
| `monitoring` | CloudWatch monitoring state (`enabled`/`disabled`) |
| `tags` | All resource tags as a dict |

---

### Lambda Functions
**Entity ID:** `sensor.aws_{account}_{region}_lambda_{function_name}`
**Native value:** Runtime (e.g. `python3.12`, `nodejs20.x`)

| Attribute | Description |
|-----------|-------------|
| `function_name` | Lambda function name |
| `runtime` | Execution runtime |
| `memory_size` | Allocated memory in MB |
| `timeout` | Maximum execution time in seconds |
| `code_size` | Deployment package size in bytes |
| `last_modified` | Last deployment timestamp |
| `description` | Function description |
| `handler` | Entry point (e.g. `index.handler`) |
| `role` | IAM execution role name |
| `package_type` | Deployment type (`Zip` or `Image`) |
| `architectures` | CPU architecture list (`x86_64`, `arm64`) |
| `ephemeral_storage_mb` | `/tmp` storage size in MB (512–10240) |
| `layers_count` | Number of Lambda layers attached |

---

### Auto Scaling Groups
**Entity ID:** `sensor.aws_{account}_{region}_auto_scaling_group_{name}`
**Native value:** Current instance count

| Attribute | Description |
|-----------|-------------|
| `name` | ASG name |
| `desired_capacity` | Target number of instances |
| `min_size` | Minimum allowed instances |
| `max_size` | Maximum allowed instances |
| `instances` | Current instance count |
| `health_check_type` | Health check method (`EC2` or `ELB`) |
| `availability_zones` | List of AZs the ASG spans |
| `launch_template` | Launch template or configuration name |
| `launch_template_version` | Launch template version in use |
| `suspended_processes` | List of suspended scaling processes |
| `termination_policies` | List of instance termination policies |
| `created_time` | When the ASG was created |

---

### ECS Clusters
**Entity ID:** `sensor.aws_{account}_{region}_ecs_{cluster_name}`
**Native value:** Running task count

| Attribute | Description |
|-----------|-------------|
| `name` | Cluster name |
| `arn` | Cluster ARN |
| `status` | Cluster status (`ACTIVE`, `INACTIVE`) |
| `running_tasks` | Number of running tasks |
| `pending_tasks` | Number of pending tasks |
| `active_services` | Number of active services |
| `registered_instances` | Number of registered container instances |

---

### EKS Clusters
**Entity ID:** `sensor.aws_{account}_{region}_eks_{cluster_name}`
**Native value:** Cluster status (`ACTIVE`, `CREATING`, etc.)

| Attribute | Description |
|-----------|-------------|
| `name` | Cluster name |
| `arn` | Cluster ARN |
| `status` | Cluster status |
| `version` | Kubernetes version |
| `endpoint` | API server endpoint URL |
| `created_at` | Cluster creation timestamp |

---

### Elastic Beanstalk Environments
**Entity ID:** `sensor.aws_{account}_{region}_beanstalk_{env_name}`
**Native value:** Environment health (`Green`, `Yellow`, `Red`, `Grey`)

| Attribute | Description |
|-----------|-------------|
| `name` | Environment name |
| `id` | Environment ID |
| `application_name` | Parent application name |
| `status` | Environment status (`Ready`, `Launching`, etc.) |
| `health` | Health colour (`Green`, `Yellow`, `Red`, `Grey`) |
| `health_status` | Detailed health status |
| `platform_arn` | Platform ARN |
| `solution_stack` | Solution stack name |
| `tier_name` | Tier name (`WebServer` or `Worker`) |
| `tier_type` | Tier type (`Standard` or `SQS/HTTP`) |
| `cname` | CNAME URL |
| `endpoint_url` | Load balancer endpoint URL |
| `date_created` | Environment creation timestamp |
| `date_updated` | Last update timestamp |

---

## Databases & Storage

### RDS Databases
**Entity ID:** `sensor.aws_{account}_{region}_rds_{db_identifier}`
**Native value:** DB status (`available`, `stopped`, `creating`, etc.)

| Attribute | Description |
|-----------|-------------|
| `db_instance_identifier` | DB instance identifier |
| `db_instance_class` | Instance type (e.g. `db.t3.micro`) |
| `engine` | Database engine (`mysql`, `postgres`, etc.) |
| `engine_version` | Engine version string |
| `status` | Current DB status |
| `allocated_storage` | Allocated storage in GB |
| `storage_type` | Storage type (`gp2`, `gp3`, `io1`, `standard`) |
| `multi_az` | Whether Multi-AZ deployment is enabled |
| `publicly_accessible` | Whether the DB is publicly accessible |
| `deletion_protection` | Whether deletion protection is enabled |
| `backup_retention_days` | Automated backup retention in days |
| `performance_insights` | Whether Performance Insights is enabled |
| `endpoint` | DB hostname endpoint |
| `port` | DB connection port |
| `vpc_id` | VPC the DB belongs to |
| `availability_zone` | AZ where the primary instance runs |
| `ca_certificate` | CA certificate identifier |

---

### DynamoDB Tables
**Entity ID:** `sensor.aws_{account}_{region}_dynamodb_{table_name}`
**Native value:** Table status (`ACTIVE`, `CREATING`, etc.)

| Attribute | Description |
|-----------|-------------|
| `table_name` | Table name |
| `status` | Table status |
| `item_count` | Approximate number of items |
| `size_bytes` | Approximate table size in bytes |
| `created` | Table creation timestamp |
| `billing_mode` | `PROVISIONED` or `PAY_PER_REQUEST` |
| `read_capacity_units` | Provisioned RCU (0 if on-demand) |
| `write_capacity_units` | Provisioned WCU (0 if on-demand) |
| `stream_enabled` | Whether DynamoDB Streams is enabled |
| `encryption_type` | Encryption status (`ENABLED`, `DISABLED`) |
| `global_indexes` | Number of Global Secondary Indexes |
| `local_indexes` | Number of Local Secondary Indexes |
| `table_class` | Table class (`STANDARD` or `STANDARD_INFREQUENT_ACCESS`) |

---

### ElastiCache Clusters
**Entity ID:** `sensor.aws_{account}_{region}_elasticache_{cluster_id}`
**Native value:** Cluster status (`available`, `creating`, etc.)

| Attribute | Description |
|-----------|-------------|
| `cluster_id` | Cache cluster ID |
| `status` | Cluster status |
| `engine` | Cache engine (`redis` or `memcached`) |
| `engine_version` | Engine version string |
| `node_type` | Node type (e.g. `cache.t3.micro`) |
| `num_nodes` | Number of cache nodes |
| `preferred_az` | Preferred availability zone |
| `parameter_group` | Cache parameter group name |
| `snapshot_retention_days` | Automated snapshot retention in days |
| `at_rest_encryption` | Whether at-rest encryption is enabled |
| `in_transit_encryption` | Whether in-transit encryption is enabled |
| `replication_group_id` | Replication group ID (Redis clusters) |
| `auto_minor_version_upgrade` | Whether minor version auto-upgrade is enabled |

---

### S3 Buckets
**Entity ID:** `sensor.aws_{account}_{region}_s3_bucket_{bucket_name}`
**Native value:** Bucket region

| Attribute | Description |
|-----------|-------------|
| `name` | Bucket name |
| `region` | AWS region the bucket is in |
| `created` | Bucket creation timestamp |

---

### EBS Volume Count
**Entity ID:** `sensor.aws_{account}_{region}_ebs_count`
**Native value:** Total number of EBS volumes in the region
*(Only created when "Create individual count sensors" is enabled in integration options.)*

| Attribute | Description |
|-----------|-------------|
| `total_volumes` | Total number of EBS volumes |
| `attached` | Number of volumes attached to an instance |
| `unattached` | Number of volumes not attached to any instance |
| `total_size_gb` | Combined size of all volumes in GB |
| `total_snapshots` | Total number of EBS snapshots owned in this region |
| `total_snapshot_size_gb` | Combined size of all snapshots in GB |
| `snapshots_truncated` | `True` if there are more than 50 snapshots (details sensor shows newest 50 only) |

---

### EBS Volumes
**Entity ID:** `sensor.aws_{account}_{region}_ebs_{volume_id}`
**Native value:** Volume state (`in-use`, `available`, `creating`, etc.)

| Attribute | Description |
|-----------|-------------|
| `id` | Volume ID |
| `size` | Volume size in GB |
| `type` | Volume type (`gp2`, `gp3`, `io1`, `st1`, `sc1`) |
| `iops` | Provisioned IOPS (where applicable) |
| `throughput` | Provisioned throughput in MB/s (gp3) |
| `state` | Current volume state |
| `az` | Availability zone |
| `attached_to` | Instance ID the volume is attached to |
| `encrypted` | Whether the volume is encrypted |
| `created` | Volume creation timestamp |

---

### EBS Snapshots
**Entity ID:** `sensor.aws_{account}_{region}_ebs_snapshots`
**Native value:** Total number of EBS snapshots owned by this account in the region

A single sensor per region is used rather than one sensor per snapshot, as accounts can have hundreds or thousands of snapshots. The sensor stores the most recent 50 snapshots as attributes, sorted newest-first.

| Attribute | Description |
|-----------|-------------|
| `snapshots` | List of up to 50 snapshots, each containing the fields below |
| `total_snapshot_size_gb` | Combined `VolumeSize` across **all** snapshots in the region (not just the listed 50) |
| `snapshots_truncated` | `True` if there are more than 50 snapshots; only the newest 50 are listed |

Each entry in `snapshots` contains:

| Field | Description |
|-------|-------------|
| `snapshot_id` | Snapshot ID (e.g. `snap-0abc123`) |
| `volume_id` | ID of the source volume |
| `volume_size` | Size of the source volume at time of snapshot, in GB |
| `start_time` | Snapshot creation timestamp (ISO 8601) |
| `state` | Snapshot state (`pending`, `completed`, `error`) |
| `progress` | Completion percentage (e.g. `100%`) — useful when `state` is `pending` |
| `description` | Snapshot description |
| `name` | Value of the `Name` tag, if set |
| `encrypted` | Whether the snapshot is encrypted |

---

### EFS File Systems
**Entity ID:** `sensor.aws_{account}_{region}_efs_fs_{fs_id}`
**Native value:** File system lifecycle state (`available`, `creating`, etc.)

| Attribute | Description |
|-----------|-------------|
| `id` | File system ID |
| `name` | Name tag value |
| `state` | Lifecycle state |
| `size_bytes` | Current size in bytes |
| `size_gb` | Current size in GB |
| `number_of_mount_targets` | Number of mount targets |
| `performance_mode` | Performance mode (`generalPurpose` or `maxIO`) |
| `throughput_mode` | Throughput mode (`bursting`, `provisioned`, `elastic`) |
| `encrypted` | Whether at-rest encryption is enabled |
| `availability_zone` | AZ for single-zone file systems |
| `created_time` | Creation timestamp |
| `tags` | All resource tags as a dict |

---

### ECR Repositories
**Entity ID:** `sensor.aws_{account}_{region}_ecr_{repo_name}`
**Native value:** Image count

| Attribute | Description |
|-----------|-------------|
| `name` | Repository name |
| `arn` | Repository ARN |
| `uri` | Repository URI for pushing/pulling images |
| `image_count` | Number of images in the repository |
| `image_tag_mutability` | Tag mutability setting (`MUTABLE`/`IMMUTABLE`) |
| `scan_on_push` | Whether images are scanned on push |
| `encryption_type` | Encryption type (`AES256` or `KMS`) |
| `created_at` | Repository creation timestamp |

---

### Redshift Clusters
**Entity ID:** `sensor.aws_{account}_{region}_redshift_{cluster_id}`
**Native value:** Cluster status (`available`, `paused`, `creating`, etc.)

| Attribute | Description |
|-----------|-------------|
| `identifier` | Cluster identifier |
| `status` | Current cluster status |
| `node_type` | Node type (e.g. `dc2.large`) |
| `number_of_nodes` | Number of nodes in the cluster |
| `db_name` | Default database name |
| `endpoint` | Cluster hostname endpoint |
| `port` | Connection port |
| `vpc_id` | VPC the cluster belongs to |
| `availability_zone` | Availability zone |
| `encrypted` | Whether the cluster is encrypted |
| `publicly_accessible` | Whether the cluster is publicly accessible |
| `cluster_version` | Cluster version |
| `engine_version` | Full engine version string |
| `master_username` | Master username |
| `created_time` | Cluster creation timestamp |

---

## Networking

### VPCs
**Entity ID:** `sensor.aws_{account}_{region}_vpc_vpc_{vpc_id}`
**Native value:** VPC state (`available`, `pending`)

| Attribute | Description |
|-----------|-------------|
| `vpc_id` | VPC ID |
| `name` | Name tag value |
| `state` | VPC state |
| `cidr_block` | Primary CIDR block |
| `is_default` | Whether this is the default VPC |
| `tenancy` | Instance tenancy (`default` or `dedicated`) |
| `internet_gateway` | Internet gateway ID if attached |
| `nat_gateways` | List of NAT gateway IDs |
| `nat_gateway_count` | Number of NAT gateways |
| `peering_connection_count` | Number of VPC peering connections |
| `vpn_connection_count` | Number of VPN connections |
| `subnet_count` | Total number of subnets |
| `public_subnet_count` | Number of public subnets |
| `private_subnet_count` | Number of private subnets |
| `subnets` | List of subnet details (up to 20) |
| `subnets_truncated` | True if subnet list was truncated |

---

### ALB / NLB Load Balancers
**Entity ID:** `sensor.aws_{account}_{region}_load_balancer_{name}`
**Native value:** Load balancer state (`active`, `provisioning`, etc.)

| Attribute | Description |
|-----------|-------------|
| `name` | Load balancer name |
| `dns_name` | DNS name for routing traffic |
| `type` | Type (`application` or `network`) |
| `scheme` | Scheme (`internet-facing` or `internal`) |
| `state` | Current state |
| `vpc_id` | VPC the load balancer is in |

---

### Classic Load Balancers
**Entity ID:** `sensor.aws_{account}_{region}_classic_lb_{name}`
**Native value:** Instance count

| Attribute | Description |
|-----------|-------------|
| `name` | Load balancer name |
| `dns_name` | DNS name |
| `scheme` | Scheme (`internet-facing` or `internal`) |
| `vpc_id` | VPC ID |
| `availability_zones` | List of AZs |
| `subnets` | List of subnet IDs |
| `security_groups` | List of security group IDs |
| `instances` | List of attached instance IDs |
| `instance_count` | Number of attached instances |
| `listeners` | List of listener configurations |
| `health_check_target` | Health check target string |
| `health_check_interval` | Health check interval in seconds |
| `created_time` | Creation timestamp |

---

### Elastic IPs
**Entity ID:** `sensor.aws_{account}_{region}_eip_{ip_address}`
**Native value:** IP address

| Attribute | Description |
|-----------|-------------|
| `ip` | Public IP address |
| `allocation_id` | Allocation ID |
| `associated_with` | Instance or network interface ID it's attached to |
| `domain` | Domain type (`vpc` or `standard`) |
| `attached` | Whether the EIP is currently attached |

---

### API Gateway
**Entity ID:** `sensor.aws_{account}_{region}_apigw_{api_id}`
**Native value:** API type (`REST`, `HTTP`, `WEBSOCKET`)

| Attribute | Description |
|-----------|-------------|
| `id` | API ID |
| `name` | API name |
| `type` | Protocol type |
| `description` | API description |
| `endpoint_type` | Endpoint type (`EDGE`, `REGIONAL`, `PRIVATE`) |
| `created_date` | API creation timestamp |
| `api_endpoint` | Invoke URL (HTTP/WebSocket APIs) |

---

### CloudFront Distributions
**Entity ID:** `sensor.aws_{account}_global_cloudfront_{distribution_id}`
**Native value:** Distribution status (`Deployed`, `InProgress`)

| Attribute | Description |
|-----------|-------------|
| `id` | Distribution ID |
| `domain_name` | CloudFront domain name |
| `status` | Deployment status |
| `enabled` | Whether the distribution is enabled |
| `http_version` | HTTP version supported (`http2`, `http2and3`) |
| `price_class` | Price class (determines edge locations) |
| `origins` | List of origin domain names |
| `aliases` | List of CNAME aliases |
| `comment` | Distribution comment |
| `last_modified` | Last modification timestamp |

---

### Route 53 Hosted Zones
**Entity ID:** `sensor.aws_{account}_global_route_53_{zone_id}`
**Native value:** Record count

| Attribute | Description |
|-----------|-------------|
| `id` | Hosted zone ID |
| `name` | Domain name |
| `private` | Whether this is a private hosted zone |
| `record_count` | Number of record sets |
| `comment` | Zone comment |

---

## Messaging & Streaming

### SNS Topics
**Entity ID:** `sensor.aws_{account}_{region}_sns_{topic_name}`
**Native value:** Confirmed subscription count

| Attribute | Description |
|-----------|-------------|
| `name` | Topic name |
| `arn` | Topic ARN |
| `subscriptions` | Number of confirmed subscriptions |
| `display_name` | Display name for SMS messages |

---

### SQS Queues
**Entity ID:** `sensor.aws_{account}_{region}_sqs_{queue_name}`
**Native value:** Approximate number of available messages

| Attribute | Description |
|-----------|-------------|
| `name` | Queue name |
| `url` | Queue URL |
| `messages_available` | Approximate messages available for retrieval |
| `messages_in_flight` | Approximate messages in flight (being processed) |
| `messages_delayed` | Approximate messages in delay state |
| `created` | Queue creation Unix timestamp |
| `visibility_timeout_seconds` | How long messages are invisible after retrieval |
| `message_retention_seconds` | How long messages are retained before deletion |
| `max_message_size_bytes` | Maximum message size in bytes |
| `delay_seconds` | Default delivery delay in seconds |
| `fifo` | Whether this is a FIFO queue |
| `kms_key` | KMS key ID for server-side encryption |

---

### Kinesis Streams
**Entity ID:** `sensor.aws_{account}_{region}_kinesis_{stream_name}`
**Native value:** Stream status (`ACTIVE`, `CREATING`, etc.)

| Attribute | Description |
|-----------|-------------|
| `name` | Stream name |
| `arn` | Stream ARN |
| `status` | Current stream status |
| `stream_mode` | Mode (`PROVISIONED` or `ON_DEMAND`) |
| `shard_count` | Number of open shards |
| `retention_hours` | Data retention period in hours |
| `consumer_count` | Number of registered consumers |

---

## Security & Compliance

### IAM Summary
**Entity ID:** `sensor.aws_{account}_global_iam_summary`
**Native value:** Total IAM user count

| Attribute | Description |
|-----------|-------------|
| `total_users` | Total number of IAM users |
| `users_no_mfa` | Users with console access but no MFA |
| `users_old_password_90d` | Users who haven't changed password in >90 days |
| `users_not_logged_in_90d` | Users who haven't logged in for >90 days |
| `users_old_keys_90d` | Users with access keys older than 90 days |
| `total_roles` | Total customer-managed roles |
| `roles_unused_90d` | Roles not used in >90 days |
| `root_mfa_enabled` | Whether root account MFA is enabled |
| `root_access_keys` | Number of root account access keys (should be 0) |
| `mfa_devices_in_use` | Total MFA devices in use |
| `total_groups` | Total number of IAM groups |
| `total_policies` | Total number of customer-managed policies |

---

### IAM Password Policy
**Entity ID:** `sensor.aws_{account}_global_iam_password_policy`
**Native value:** Maximum password age in days (None if no expiry)

| Attribute | Description |
|-----------|-------------|
| `min_length` | Minimum password length |
| `require_uppercase` | Whether uppercase characters are required |
| `require_lowercase` | Whether lowercase characters are required |
| `require_numbers` | Whether numbers are required |
| `require_symbols` | Whether symbols are required |
| `allow_users_to_change` | Whether users can change their own password |
| `expire_passwords` | Whether passwords expire |
| `max_password_age` | Maximum password age in days |
| `password_reuse_prevention` | Number of previous passwords that cannot be reused |
| `hard_expiry` | Whether users are locked out when password expires |

---

### IAM Users
**Entity ID:** `sensor.aws_{account}_global_iam_user_{username}`
**Native value:** Days since last console login (None if never logged in)

| Attribute | Description |
|-----------|-------------|
| `username` | IAM username |
| `arn` | User ARN |
| `password_enabled` | Whether console access is enabled |
| `mfa_active` | Whether MFA is active |
| `password_last_changed_days` | Days since password was last changed |
| `password_last_used_days` | Days since last console login |
| `key1_active` | Whether access key 1 is active |
| `key1_age_days` | Age of access key 1 in days |
| `key1_last_used_days` | Days since access key 1 was last used |
| `key2_active` | Whether access key 2 is active |
| `key2_age_days` | Age of access key 2 in days |
| `key2_last_used_days` | Days since access key 2 was last used |
| `oldest_key_age_days` | Age of the oldest active key in days |
| `active_key_count` | Number of active access keys (0, 1 or 2) |

---

### IAM Roles (Customer-Managed)
**Entity ID:** `sensor.aws_{account}_global_iam_role_{role_name}`
**Native value:** Days since last used (None if never used)

| Attribute | Description |
|-----------|-------------|
| `name` | Role name |
| `arn` | Role ARN |
| `path` | Role path |
| `description` | Role description |
| `last_used_days` | Days since the role was last assumed |
| `last_used_region` | AWS region where the role was last used |
| `created_days_ago` | Days since the role was created |
| `max_session_duration` | Maximum session duration in seconds |
| `has_permissions_boundary` | Whether a permissions boundary is attached |

---

### ACM Certificates
**Entity ID:** `sensor.aws_{account}_{region}_acm_{cert_id}`
**Native value:** Days until expiry (negative if already expired)

| Attribute | Description |
|-----------|-------------|
| `arn` | Certificate ARN |
| `domain_name` | Primary domain name |
| `subject_alternative_names` | List of additional domain names |
| `status` | Certificate status (`ISSUED`, `PENDING_VALIDATION`, etc.) |
| `type` | Certificate type (`AMAZON_ISSUED` or `IMPORTED`) |
| `issuer` | Certificate issuer |
| `key_algorithm` | Key algorithm (`RSA_2048`, `EC_prime256v1`, etc.) |
| `not_before` | Certificate validity start date |
| `not_after` | Certificate expiry date |
| `days_until_expiry` | Days remaining until expiry |
| `renewal_eligibility` | Whether eligible for managed renewal |
| `in_use_by` | List of resources using this certificate |

---

### CloudTrail Trails
**Entity ID:** `sensor.aws_{account}_{region}_cloudtrail_{trail_name}`
**Native value:** Logging status (`True`/`False`)

| Attribute | Description |
|-----------|-------------|
| `name` | Trail name |
| `arn` | Trail ARN |
| `home_region` | Region where the trail was created |
| `is_logging` | Whether the trail is currently logging |
| `is_multi_region` | Whether the trail covers all regions |
| `is_organization` | Whether this is an organisation trail |
| `log_file_validation` | Whether log file integrity validation is enabled |
| `s3_bucket` | S3 bucket where logs are delivered |
| `cloudwatch_logs_arn` | CloudWatch Logs group ARN, if configured |
| `kms_key_id` | KMS key ID for log encryption |
| `management_events` | Management event logging status |
| `data_event_count` | Number of data event selectors |
| `latest_delivery` | Timestamp of last successful log delivery |
| `latest_error` | Last delivery error message |
| `latest_digest` | Timestamp of last digest delivery |

---

## Monitoring & Cost

### CloudWatch Alarms
**Entity ID:** `sensor.aws_{account}_{region}_alarm_{alarm_name}`
**Native value:** Alarm state (`OK`, `ALARM`, `INSUFFICIENT_DATA`)

| Attribute | Description |
|-----------|-------------|
| `name` | Alarm name |
| `state` | Current state |
| `reason` | Reason for the current state |
| `metric` | CloudWatch metric name being monitored |
| `namespace` | CloudWatch metric namespace |
| `enabled` | Whether alarm actions are enabled |

---

### Cost Explorer
**Entity ID:** `sensor.aws_{account}_global_cost_yesterday`
**Native value:** Yesterday's total cost in USD

| Attribute | Description |
|-----------|-------------|
| `cost_mtd` | Raw month-to-date cost response |
| `service_costs` | Top 10 services by cost yesterday with name, amount, rank, percentage |

**Entity ID:** `sensor.aws_{account}_global_cost_mtd`
**Native value:** Month-to-date cost in USD

---

## Summary Sensors

### Regional Summary
**Entity ID:** `sensor.aws_{account}_{region}_summary`
**Native value:** Total resource count for that region

Contains counts for all services in that region as attributes, including `ebs_snapshots` and `ebs_snapshot_size_gb`.

---

### Global Summary
**Entity ID:** `sensor.aws_{account}_global_summary`
**Native value:** Total resource count across all regions

| Attribute | Description |
|-----------|-------------|
| `ec2_running` | Running EC2 instances |
| `ec2_stopped` | Stopped EC2 instances |
| `lambda_functions` | Lambda functions |
| `ecs_clusters` | ECS clusters |
| `eks_clusters` | EKS clusters |
| `auto_scaling_groups` | Auto Scaling Groups |
| `beanstalk_environments` | Elastic Beanstalk environments |
| `rds_instances` | RDS database instances |
| `dynamodb_tables` | DynamoDB tables |
| `elasticache_clusters` | ElastiCache clusters |
| `s3_buckets` | S3 buckets |
| `ebs_volumes` | EBS volumes |
| `ebs_attached` | EBS volumes attached to an instance |
| `ebs_unattached` | EBS volumes not attached to any instance |
| `ebs_snapshots` | EBS snapshots (across all monitored regions) |
| `ebs_snapshot_size_gb` | Combined size of all EBS snapshots in GB |
| `efs_file_systems` | EFS file systems |
| `ecr_repositories` | ECR repositories |
| `redshift_clusters` | Redshift clusters |
| `vpcs` | VPCs |
| `load_balancers` | ALB/NLB load balancers |
| `classic_load_balancers` | Classic load balancers |
| `elastic_ips` | Elastic IPs |
| `elastic_ips_unattached` | Unattached Elastic IPs |
| `api_gateways` | API Gateways |
| `cloudfront_distributions` | CloudFront distributions |
| `route53_zones` | Route 53 hosted zones |
| `sns_topics` | SNS topics |
| `sqs_queues` | SQS queues |
| `kinesis_streams` | Kinesis streams |
| `acm_certificates` | ACM certificates |
| `acm_expiring_30d` | ACM certificates expiring within 30 days |
| `cloudtrail_trails` | CloudTrail trails |
| `cloudtrail_logging` | CloudTrail trails actively logging |
| `cloudwatch_alarms` | CloudWatch alarms |
| `cloudwatch_alarms_alarm` | CloudWatch alarms in ALARM state |
| `iam_users` | IAM users |
| `iam_users_no_mfa` | IAM users with console access but no MFA |
| `iam_users_old_password` | IAM users with password unchanged >90 days |
| `iam_users_old_keys` | IAM users with access keys >90 days old |
| `iam_roles` | Customer-managed IAM roles |
| `iam_roles_unused_90d` | IAM roles unused for >90 days |
