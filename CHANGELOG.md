# Changelog

All notable changes to this project will be documented in this file.

## [1.9.0] - 2026-05-07

### New Features

- **EBS Snapshot monitoring** — EBS snapshot data is now fetched alongside volumes using the same coordinator and refresh interval.

  - **`sensor.aws_{account}_{region}_ebs_snapshots`** — new sensor per region reporting the total snapshot count as its native value, with the most recent 50 snapshots (sorted newest-first) as attributes, plus total snapshot storage consumed across all snapshots in the region. If an account has more than 50 snapshots the `snapshots_truncated` attribute is set to `True`.

  - **`sensor.aws_{account}_{region}_ebs_count`** — now also reports `total_snapshots`, `total_snapshot_size_gb`, and `snapshots_truncated` in its attributes alongside the existing volume breakdown.

  - **Regional summary sensors** (`sensor.aws_{account}_{region}_summary`) — now include `ebs_snapshots` and `ebs_snapshot_size_gb` attributes.

  - **Global summary sensor** (`sensor.aws_{account}_global_summary`) — now includes `ebs_snapshots` and `ebs_snapshot_size_gb` attributes, aggregated across all monitored regions.

### IAM Policy Change — Action Required for Existing Users

The EBS coordinator now calls `ec2:DescribeSnapshots` in addition to `ec2:DescribeVolumes`. **Existing users who have EBS Volumes enabled must add `ec2:DescribeSnapshots` to their IAM policy** before upgrading, otherwise snapshot data will be absent and a one-time permission warning will appear in the logs.

Users who did not previously have EBS enabled are unaffected — the updated minimum policy is shown automatically during setup.

---

## [1.2.0] - 2026-03-10

### Breaking Changes

- **Legacy cost sensors removed**: `sensor.aws_{account}_{region}_cost_today` and
  `sensor.aws_{account}_{region}_cost_mtd` have been removed. Use the replacement
  sensors `sensor.aws_{account}_cost_yesterday` and `sensor.aws_{account}_cost_month_to_date`
  instead. Update any dashboard cards or automations referencing the old entity IDs.

### Bug Fixes

- **CRITICAL** Fixed `AwsEc2CountSensor` called with 3 arguments but constructor required 4
  (`state_filter` was missing). The sensor now counts all instances and reports
  running/stopped as attributes instead.
- **CRITICAL** `AwsGlobalSummarySensor` now inherits from `CoordinatorEntity` so it
  receives update callbacks — previously it showed stale data after initial load.
- **CRITICAL** Fixed services (`refresh_account`, `refresh_all_accounts`) never being
  registered due to `hasattr` being used against a dict (always returned `True`).
- **CRITICAL** Fixed `async_update_options` reading region changes from `entry.data`
  instead of `entry.options`, causing region deselections to be silently ignored.
- **CRITICAL** Fixed month-to-date cost query crashing on the 1st of the month when
  `Start == End`. End date is now set to tomorrow (End is exclusive in AWS API),
  which also captures today's partial costs.
- **HIGH** Fixed inverted `skip_initial_refresh` logic — the `True` branch was still
  calling `async_refresh()`. Now correctly skips all refresh on startup.

### Improvements

- `device_info` migrated from raw dicts to proper `DeviceInfo(entry_type=DeviceEntryType.SERVICE)`
  objects across all sensor classes.
- `last_updated` (native `datetime`) added to `extra_state_attributes` on all sensors.
- Sensor friendly names standardised to full service names (e.g. "Load Balancer",
  "Auto Scaling Group") rather than abbreviations.
- `AwsGlobalSummarySensor` name now includes account name to avoid clashes when
  multiple AWS accounts are configured.
- Removed duplicate `_attr_icon` in `AwsCostMtdSensor`.
- Removed dead `get_elb_client()` method from `aws_client.py`.
- `boto3` and `botocore` version pins relaxed from exact `==1.35.76` to
  `>=1.35.0,<2.0.0` to reduce conflicts with other integrations.
- Dashboard YAML files moved to `dashboards/` subdirectory.
- `f-string` logging replaced with `%s`-style throughout `__init__.py`.
- Duplicate `PLATFORMS` constant removed from `const.py`.
- "Korean" removed from supported languages list (was never included in translations).

## [1.0.0] - Initial Release

- Initial release with support for 15 AWS services across multiple regions.
- Cost tracking (daily, MTD, per-service).
- Multi-region and multi-account support.
- 13 language translations.
