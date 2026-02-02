"""
AWS billing data collector.
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .base import BaseCollector, BillingData, ResourceData
from ..core.exceptions import CollectorError, APIError


class AWSCollector(BaseCollector):
    """AWS billing data collector using Cost Explorer and Resource APIs."""
    
    def __init__(self, config: Any, credentials: Dict[str, str]):
        super().__init__(config, credentials)
        self.session = None
        self.ce_client = None
        self.ec2_client = None
        self.rds_client = None
        self.lambda_client = None
    
    def authenticate(self) -> None:
        """Authenticate with AWS using provided credentials."""
        try:
            if self.credentials.get("session_token"):
                self.session = boto3.Session(
                    aws_access_key_id=self.credentials["access_key_id"],
                    aws_secret_access_key=self.credentials["secret_access_key"],
                    aws_session_token=self.credentials["session_token"],
                    region_name="us-east-1"  # Cost Explorer is in us-east-1
                )
            else:
                self.session = boto3.Session(
                    aws_access_key_id=self.credentials["access_key_id"],
                    aws_secret_access_key=self.credentials["secret_access_key"],
                    region_name="us-east-1"
                )
            
            # Initialize clients
            self.ce_client = self.session.client('ce')
            self.ec2_client = self.session.client('ec2')
            self.rds_client = self.session.client('rds')
            self.lambda_client = self.session.client('lambda')
            
            # Test authentication
            self.ce_client.get_dimension_values(
                TimePeriod={'Start': '2023-01-01', 'End': '2023-01-02'},
                Dimension='SERVICE'
            )
            
        except Exception as e:
            raise APIError(f"AWS authentication failed: {e}")
    
    def collect_billing_data(self, start_date: datetime, end_date: datetime) -> List[BillingData]:
        """Collect AWS billing data using Cost Explorer."""
        self.validate_date_range(start_date, end_date)
        
        try:
            billing_data = []
            
            # Get cost and usage data
            time_period = {
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            }
            
            # Get detailed cost data
            response = self.ce_client.get_cost_and_usage(
                TimePeriod=time_period,
                Granularity='DAILY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'REGION'},
                    {'Type': 'DIMENSION', 'Key': 'RESOURCE_ID'},
                    {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
                ]
            )
            
            # Process results
            for result in response.get('ResultsByTime', []):
                period_start = datetime.strptime(result['TimePeriod']['Start'], '%Y-%m-%d')
                period_end = datetime.strptime(result['TimePeriod']['End'], '%Y-%m-%d')
                
                for group in result.get('Groups', []):
                    keys = group['Keys']
                    metrics = group['Metrics']
                    
                    # Parse dimensions
                    service = self._extract_dimension(keys, 'SERVICE')
                    region = self._extract_dimension(keys, 'REGION')
                    resource_id = self._extract_dimension(keys, 'RESOURCE_ID')
                    usage_type = self._extract_dimension(keys, 'USAGE_TYPE')
                    
                    # Parse metrics
                    blended_cost = float(metrics['BlendedCost']['Amount'])
                    usage_quantity = float(metrics['UsageQuantity']['Amount'])
                    usage_unit = metrics['UsageQuantity']['Unit']
                    currency = metrics['BlendedCost']['Unit']
                    
                    # Get resource details and tags
                    resource_tags = self._get_resource_tags(resource_id, service)
                    
                    billing_entry = BillingData(
                        provider="aws",
                        account_id=self.config.aws.account_id,
                        service=service,
                        region=region,
                        resource_id=resource_id,
                        resource_name=resource_tags.get('Name', resource_id),
                        usage_type=usage_type,
                        usage_amount=usage_quantity,
                        usage_unit=usage_unit,
                        cost=blended_cost,
                        currency=currency,
                        start_time=period_start,
                        end_time=period_end,
                        tags=resource_tags,
                        environment=self.extract_environment_from_tags(
                            resource_tags, self.config.aws.environment_tag
                        ),
                        cost_center=self.extract_cost_center_from_tags(
                            resource_tags, self.config.aws.cost_center_tag
                        )
                    )
                    
                    billing_data.append(billing_entry)
            
            return billing_data
            
        except Exception as e:
            raise CollectorError(f"Failed to collect AWS billing data: {e}")
    
    def collect_resource_data(self) -> List[ResourceData]:
        """Collect AWS resource inventory data."""
        try:
            resources = []
            
            # Collect EC2 instances
            resources.extend(self._collect_ec2_instances())
            
            # Collect RDS instances
            resources.extend(self._collect_rds_instances())
            
            # Collect Lambda functions
            resources.extend(self._collect_lambda_functions())
            
            # Collect S3 buckets
            resources.extend(self._collect_s3_buckets())
            
            return resources
            
        except Exception as e:
            raise CollectorError(f"Failed to collect AWS resource data: {e}")
    
    def get_cost_breakdown(self, start_date: datetime, end_date: datetime, 
                          group_by: str = "service") -> Dict[str, float]:
        """Get AWS cost breakdown by specified grouping."""
        self.validate_date_range(start_date, end_date)
        
        try:
            time_period = {
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            }
            
            # Map group_by to Cost Explorer dimension
            dimension_map = {
                "service": "SERVICE",
                "region": "REGION",
                "usage_type": "USAGE_TYPE"
            }
            
            dimension = dimension_map.get(group_by, "SERVICE")
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod=time_period,
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': dimension}
                ]
            )
            
            cost_breakdown = {}
            
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    key = group['Keys'][0] if group['Keys'] else 'Unknown'
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    
                    if key not in cost_breakdown:
                        cost_breakdown[key] = 0.0
                    cost_breakdown[key] += cost
            
            return cost_breakdown
            
        except Exception as e:
            raise CollectorError(f"Failed to get AWS cost breakdown: {e}")
    
    def _extract_dimension(self, keys: List[str], dimension: str) -> str:
        """Extract dimension value from keys."""
        for key in keys:
            if key.startswith(f"{dimension}$"):
                return key.split("$", 1)[1]
        return "Unknown"
    
    def _get_resource_tags(self, resource_id: str, service: str) -> Dict[str, str]:
        """Get tags for a specific resource."""
        try:
            if service == "Amazon EC2" and resource_id.startswith("i-"):
                return self._get_ec2_tags(resource_id)
            elif service == "Amazon RDS" and resource_id.startswith("db-"):
                return self._get_rds_tags(resource_id)
            elif service == "AWS Lambda" and ":" in resource_id:
                return self._get_lambda_tags(resource_id)
            elif service == "Amazon S3":
                return self._get_s3_tags(resource_id)
            else:
                return {}
        except Exception:
            return {}
    
    def _get_ec2_tags(self, instance_id: str) -> Dict[str, str]:
        """Get EC2 instance tags."""
        try:
            response = self.ec2_client.describe_tags(
                Filters=[{'Name': 'resource-id', 'Values': [instance_id]}]
            )
            return {tag['Key']: tag['Value'] for tag in response['Tags']}
        except Exception:
            return {}
    
    def _get_rds_tags(self, db_instance_id: str) -> Dict[str, str]:
        """Get RDS instance tags."""
        try:
            response = self.rds_client.list_tags_for_resource(
                ResourceName=f"arn:aws:rds:*:*:db:{db_instance_id}"
            )
            return {tag['Key']: tag['Value'] for tag in response['TagList']}
        except Exception:
            return {}
    
    def _get_lambda_tags(self, function_arn: str) -> Dict[str, str]:
        """Get Lambda function tags."""
        try:
            function_name = function_arn.split(":")[-1]
            response = self.lambda_client.list_tags(
                Resource=function_arn
            )
            return {tag['Key']: tag['Value'] for tag in response['Tags']}
        except Exception:
            return {}
    
    def _get_s3_tags(self, bucket_name: str) -> Dict[str, str]:
        """Get S3 bucket tags."""
        try:
            s3_client = self.session.client('s3')
            response = s3_client.get_bucket_tagging(Bucket=bucket_name)
            return {tag['Key']: tag['Value'] for tag in response['TagSet']}
        except Exception:
            return {}
    
    def _collect_ec2_instances(self) -> List[ResourceData]:
        """Collect EC2 instance data."""
        resources = []
        
        try:
            response = self.ec2_client.describe_instances()
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    tags = self.standardize_tags({
                        tag['Key']: tag['Value'] for tag in instance.get('Tags', [])
                    })
                    
                    resource = ResourceData(
                        provider="aws",
                        account_id=self.config.aws.account_id,
                        resource_id=instance['InstanceId'],
                        resource_name=tags.get('Name', instance['InstanceId']),
                        resource_type="EC2 Instance",
                        region=instance['Placement']['AvailabilityZone'][:-1],
                        state=instance['State']['Name'],
                        creation_time=instance['LaunchTime'],
                        tags=tags,
                        environment=self.extract_environment_from_tags(
                            tags, self.config.aws.environment_tag
                        ),
                        cost_center=self.extract_cost_center_from_tags(
                            tags, self.config.aws.cost_center_tag
                        ),
                        is_idle=self._is_ec2_idle(instance),
                        last_used_time=self._get_ec2_last_used(instance)
                    )
                    
                    resources.append(resource)
                    
        except Exception as e:
            raise CollectorError(f"Failed to collect EC2 instances: {e}")
        
        return resources
    
    def _collect_rds_instances(self) -> List[ResourceData]:
        """Collect RDS instance data."""
        resources = []
        
        try:
            response = self.rds_client.describe_db_instances()
            
            for db_instance in response['DBInstances']:
                tags = self._get_rds_tags(db_instance['DBInstanceIdentifier'])
                
                resource = ResourceData(
                    provider="aws",
                    account_id=self.config.aws.account_id,
                    resource_id=db_instance['DBInstanceIdentifier'],
                    resource_name=db_instance['DBInstanceIdentifier'],
                    resource_type="RDS Instance",
                    region=db_instance['AvailabilityZone'][:-1],
                    state=db_instance['DBInstanceStatus'],
                    creation_time=db_instance['InstanceCreateTime'],
                    tags=tags,
                    environment=self.extract_environment_from_tags(
                        tags, self.config.aws.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        tags, self.config.aws.cost_center_tag
                    ),
                    is_idle=self._is_rds_idle(db_instance),
                    last_used_time=None  # RDS usage tracking is more complex
                )
                
                resources.append(resource)
                
        except Exception as e:
            raise CollectorError(f"Failed to collect RDS instances: {e}")
        
        return resources
    
    def _collect_lambda_functions(self) -> List[ResourceData]:
        """Collect Lambda function data."""
        resources = []
        
        try:
            response = self.lambda_client.list_functions()
            
            for function in response['Functions']:
                tags = self._get_lambda_tags(function['FunctionArn'])
                
                resource = ResourceData(
                    provider="aws",
                    account_id=self.config.aws.account_id,
                    resource_id=function['FunctionArn'],
                    resource_name=function['FunctionName'],
                    resource_type="Lambda Function",
                    region=function['FunctionArn'].split(":")[3],
                    state="Active",
                    creation_time=datetime.fromisoformat(function['LastModified'].replace('Z', '+00:00')),
                    tags=tags,
                    environment=self.extract_environment_from_tags(
                        tags, self.config.aws.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        tags, self.config.aws.cost_center_tag
                    ),
                    is_idle=self._is_lambda_idle(function),
                    last_used_time=self._get_lambda_last_used(function)
                )
                
                resources.append(resource)
                
        except Exception as e:
            raise CollectorError(f"Failed to collect Lambda functions: {e}")
        
        return resources
    
    def _collect_s3_buckets(self) -> List[ResourceData]:
        """Collect S3 bucket data."""
        resources = []
        
        try:
            s3_client = self.session.client('s3')
            response = s3_client.list_buckets()
            
            for bucket in response['Buckets']:
                tags = self._get_s3_tags(bucket['Name'])
                
                # Get bucket location
                try:
                    location_response = s3_client.get_bucket_location(Bucket=bucket['Name'])
                    region = location_response['LocationConstraint'] or 'us-east-1'
                except:
                    region = 'Unknown'
                
                resource = ResourceData(
                    provider="aws",
                    account_id=self.config.aws.account_id,
                    resource_id=bucket['Name'],
                    resource_name=bucket['Name'],
                    resource_type="S3 Bucket",
                    region=region,
                    state="Active",
                    creation_time=bucket['CreationDate'],
                    tags=tags,
                    environment=self.extract_environment_from_tags(
                        tags, self.config.aws.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        tags, self.config.aws.cost_center_tag
                    ),
                    is_idle=self._is_s3_idle(bucket['Name']),
                    last_used_time=self._get_s3_last_used(bucket['Name'])
                )
                
                resources.append(resource)
                
        except Exception as e:
            raise CollectorError(f"Failed to collect S3 buckets: {e}")
        
        return resources
    
    def _is_ec2_idle(self, instance: Dict[str, Any]) -> bool:
        """Determine if EC2 instance is idle."""
        # Simple heuristic: stopped instances are idle
        # More sophisticated analysis would check CPU utilization, network I/O, etc.
        return instance['State']['Name'] == 'stopped'
    
    def _is_rds_idle(self, db_instance: Dict[str, Any]) -> bool:
        """Determine if RDS instance is idle."""
        return db_instance['DBInstanceStatus'] == 'stopped'
    
    def _is_lambda_idle(self, function: Dict[str, Any]) -> bool:
        """Determine if Lambda function is idle."""
        # Check last invocation time
        # This is a simplified implementation
        return False  # Would need CloudWatch metrics for accurate detection
    
    def _is_s3_idle(self, bucket_name: str) -> bool:
        """Determine if S3 bucket is idle."""
        # Check last access time
        # This is a simplified implementation
        return False  # Would need CloudWatch metrics for accurate detection
    
    def _get_ec2_last_used(self, instance: Dict[str, Any]) -> Optional[datetime]:
        """Get last used time for EC2 instance."""
        # This would require CloudWatch metrics
        return None
    
    def _get_lambda_last_used(self, function: Dict[str, Any]) -> Optional[datetime]:
        """Get last used time for Lambda function."""
        # This would require CloudWatch logs
        return None
    
    def _get_s3_last_used(self, bucket_name: str) -> Optional[datetime]:
        """Get last used time for S3 bucket."""
        # This would require CloudTrail or S3 access logs
        return None
