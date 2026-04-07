"""
Google Cloud Platform billing data collector.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from google.cloud import billing_v1
from google.cloud import compute_v1
from google.cloud import storage
from google.cloud import resourcemanager_v3
from google.oauth2 import service_account
from .base import BaseCollector, BillingData, ResourceData
from ..core.exceptions import CollectorError, APIError


class GCPCollector(BaseCollector):
    """GCP billing data collector using Google Cloud APIs."""
    
    def __init__(self, config: Any, credentials: Dict[str, str]):
        super().__init__(config, credentials)
        self.service_account_key = None
        self.credentials = None
        self.billing_client = None
        self.resource_client = None
        self.compute_client = None
        self.storage_client = None
    
    def authenticate(self) -> None:
        """Authenticate with GCP using service account credentials."""
        try:
            # Load service account credentials
            service_account_info = json.loads(self.credentials["service_account_key"])
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info
            )
            
            # Initialize clients
            self.billing_client = billing_v1.CloudBillingClient(credentials=self.credentials)
            self.resource_client = resourcemanager_v3.ProjectsClient(credentials=self.credentials)
            self.compute_client = compute_v1.InstancesClient(credentials=self.credentials)
            self.storage_client = storage.Client(credentials=self.credentials)
            
            # Test authentication
            self.resource_client.get_project(name=f"projects/{self.config.gcp.project_id}")
            
        except Exception as e:
            raise APIError(f"GCP authentication failed: {e}")
    
    def collect_billing_data(self, start_date: datetime, end_date: datetime) -> List[BillingData]:
        """Collect GCP billing data using BigQuery export."""
        self.validate_date_range(start_date, end_date)
        
        try:
            from google.cloud import bigquery
            
            billing_data = []
            
            # Initialize BigQuery client
            bq_client = bigquery.Client(credentials=self.credentials, project=self.config.gcp.project_id)
            
            # Query billing data from BigQuery export table
            # Note: This assumes billing export is configured to BigQuery
            query = f"""
            SELECT
                service.description as service,
                location.region as region,
                resource.name as resource_id,
                sku.description as usage_type,
                usage.amount as usage_amount,
                usage.unit as usage_unit,
                cost as cost,
                currency as currency,
                usage_start_time as start_time,
                usage_end_time as end_time,
                labels as tags,
                project.id as project_id
            FROM
                `{self.config.gcp.project_id}.billing_export.gcp_billing_export_v1_*`
            WHERE
                DATE(usage_start_time) >= DATE('{start_date.strftime('%Y-%m-%d')}')
                AND DATE(usage_end_time) <= DATE('{end_date.strftime('%Y-%m-%d')}')
                AND project.id = '{self.config.gcp.project_id}'
            ORDER BY
                usage_start_time DESC
            """
            
            query_job = bq_client.query(query)
            results = query_job.result()
            
            for row in results:
                # Parse tags/labels
                tags = {}
                if row.tags:
                    for label in row.tags:
                        tags[label.key] = label.value
                
                billing_entry = BillingData(
                    provider="gcp",
                    account_id=self.config.gcp.project_id,
                    service=row.service or "Unknown",
                    region=row.region or "Unknown",
                    resource_id=row.resource_id or "Unknown",
                    resource_name=row.resource_id or "Unknown",
                    usage_type=row.usage_type or "Unknown",
                    usage_amount=float(row.usage_amount) if row.usage_amount else 0.0,
                    usage_unit=row.usage_unit or "Unknown",
                    cost=float(row.cost) if row.cost else 0.0,
                    currency=row.currency or "USD",
                    start_time=row.start_time,
                    end_time=row.end_time,
                    tags=tags,
                    environment=self.extract_environment_from_tags(
                        tags, self.config.gcp.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        tags, self.config.gcp.cost_center_tag
                    )
                )
                billing_data.append(billing_entry)
            
            return billing_data
            
        except Exception as e:
            raise CollectorError(f"Failed to collect GCP billing data: {e}")
    
    def collect_resource_data(self) -> List[ResourceData]:
        """Collect GCP resource inventory data."""
        try:
            resources = []
            
            # Collect Compute Engine instances
            resources.extend(self._collect_compute_instances())
            
            # Collect Cloud Storage buckets
            resources.extend(self._collect_storage_buckets())
            
            # Collect Cloud SQL instances
            resources.extend(self._collect_sql_instances())
            
            return resources
            
        except Exception as e:
            raise CollectorError(f"Failed to collect GCP resource data: {e}")
    
    def get_cost_breakdown(self, start_date: datetime, end_date: datetime, 
                          group_by: str = "service") -> Dict[str, float]:
        """Get GCP cost breakdown by specified grouping."""
        self.validate_date_range(start_date, end_date)
        
        try:
            from google.cloud import bigquery
            
            bq_client = bigquery.Client(credentials=self.credentials, project=self.config.gcp.project_id)
            
            # Map group_by to BigQuery column
            group_column_map = {
                "service": "service.description",
                "region": "location.region",
                "project": "project.id"
            }
            
            group_column = group_column_map.get(group_by, "service.description")
            
            query = f"""
            SELECT
                {group_column} as group_key,
                SUM(cost) as total_cost
            FROM
                `{self.config.gcp.project_id}.billing_export.gcp_billing_export_v1_*`
            WHERE
                DATE(usage_start_time) >= DATE('{start_date.strftime('%Y-%m-%d')}')
                AND DATE(usage_end_time) <= DATE('{end_date.strftime('%Y-%m-%d')}')
                AND project.id = '{self.config.gcp.project_id}'
            GROUP BY
                group_key
            ORDER BY
                total_cost DESC
            """
            
            query_job = bq_client.query(query)
            results = query_job.result()
            
            cost_breakdown = {}
            for row in results:
                cost_breakdown[row.group_key or 'Unknown'] = float(row.total_cost) if row.total_cost else 0.0
            
            return cost_breakdown
            
        except Exception as e:
            raise CollectorError(f"Failed to get GCP cost breakdown: {e}")
    
    def _get_billing_account(self) -> str:
        """Get the billing account name."""
        try:
            # List billing accounts
            billing_accounts = list(self.billing_client.list_billing_accounts())
            
            # Find the billing account associated with the project
            # This is a simplified implementation
            if billing_accounts:
                return billing_accounts[0].name
            else:
                raise CollectorError("No billing accounts found")
                
        except Exception as e:
            raise CollectorError(f"Failed to get billing account: {e}")
    
    def _collect_compute_instances(self) -> List[ResourceData]:
        """Collect Compute Engine instance data."""
        resources = []
        
        try:
            # List instances in all zones
            zones = self._list_zones()
            
            for zone in zones:
                request = compute_v1.ListInstancesRequest(
                    project=self.config.gcp.project_id,
                    zone=zone
                )
                
                for instance in self.compute_client.list(request=request):
                    # Get instance tags
                    tags = self.standardize_tags(dict(instance.labels or {}))
                    
                    resource = ResourceData(
                        provider="gcp",
                        account_id=self.config.gcp.project_id,
                        resource_id=str(instance.id),
                        resource_name=instance.name,
                        resource_type="Compute Instance",
                        region=zone.rsplit('-', 1)[0],  # Extract region from zone
                        state=str(instance.status),
                        creation_time=datetime.fromisoformat(instance.creation_timestamp.rstrip('Z')),
                        tags=tags,
                        environment=self.extract_environment_from_tags(
                            tags, self.config.gcp.environment_tag
                        ),
                        cost_center=self.extract_cost_center_from_tags(
                            tags, self.config.gcp.cost_center_tag
                        ),
                        is_idle=self._is_compute_instance_idle(instance),
                        last_used_time=self._get_compute_instance_last_used(instance)
                    )
                    
                    resources.append(resource)
                    
        except Exception as e:
            raise CollectorError(f"Failed to collect GCP Compute instances: {e}")
        
        return resources
    
    def _collect_storage_buckets(self) -> List[ResourceData]:
        """Collect Cloud Storage bucket data."""
        resources = []
        
        try:
            for bucket in self.storage_client.list_buckets():
                # Get bucket labels
                labels = self.standardize_tags(bucket.labels or {})
                
                resource = ResourceData(
                    provider="gcp",
                    account_id=self.config.gcp.project_id,
                    resource_id=bucket.name,
                    resource_name=bucket.name,
                    resource_type="Storage Bucket",
                    region=bucket.location,
                    state="Active",
                    creation_time=bucket.time_created.replace(tzinfo=None),
                    tags=labels,
                    environment=self.extract_environment_from_tags(
                        labels, self.config.gcp.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        labels, self.config.gcp.cost_center_tag
                    ),
                    is_idle=self._is_storage_bucket_idle(bucket),
                    last_used_time=self._get_storage_bucket_last_used(bucket)
                )
                
                resources.append(resource)
                
        except Exception as e:
            raise CollectorError(f"Failed to collect GCP Storage buckets: {e}")
        
        return resources
    
    def _collect_sql_instances(self) -> List[ResourceData]:
        """Collect Cloud SQL instance data."""
        resources = []
        
        try:
            from google.cloud import sql_v1
            
            sql_client = sql_v1.SqlInstancesServiceClient(credentials=self.credentials)
            
            request = sql_v1.SqlInstancesListRequest(
                project=self.config.gcp.project_id
            )
            
            instances = sql_client.list(request=request)
            
            for instance in instances:
                # Get instance labels
                labels = self.standardize_tags(dict(instance.settings.user_labels or {}))
                
                resource = ResourceData(
                    provider="gcp",
                    account_id=self.config.gcp.project_id,
                    resource_id=instance.name,
                    resource_name=instance.name,
                    resource_type="Cloud SQL Instance",
                    region=instance.region or "Unknown",
                    state=instance.state.name if instance.state else "Unknown",
                    creation_time=datetime.fromisoformat(instance.create_time.rstrip('Z')) if instance.create_time else datetime.now(),
                    tags=labels,
                    environment=self.extract_environment_from_tags(
                        labels, self.config.gcp.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        labels, self.config.gcp.cost_center_tag
                    ),
                    is_idle=self._is_sql_instance_idle(instance),
                    last_used_time=self._get_sql_instance_last_used(instance)
                )
                
                resources.append(resource)
            
            return resources
            
        except Exception as e:
            raise CollectorError(f"Failed to collect GCP SQL instances: {e}")
    
    def _list_zones(self) -> List[str]:
        """List available zones in the project."""
        try:
            zones_client = compute_v1.ZonesClient(credentials=self.credentials)
            request = compute_v1.ListZonesRequest(project=self.config.gcp.project_id)
            
            zones = []
            for zone in zones_client.list(request=request):
                zones.append(zone.name)
            
            return zones
            
        except Exception as e:
            raise CollectorError(f"Failed to list GCP zones: {e}")
    
    def _is_compute_instance_idle(self, instance: Any) -> bool:
        """Determine if Compute instance is idle."""
        # Check instance status
        return str(instance.status) != 'RUNNING'
    
    def _is_storage_bucket_idle(self, bucket: Any) -> bool:
        """Determine if Storage bucket is idle."""
        # Check bucket usage metrics
        return False  # Would need storage metrics
    
    def _is_sql_instance_idle(self, instance: Any) -> bool:
        """Determine if SQL instance is idle."""
        # Check instance state and metrics
        return False  # Would need SQL metrics
    
    def _get_compute_instance_last_used(self, instance: Any) -> Optional[datetime]:
        """Get last used time for Compute instance."""
        # This would require Cloud Monitoring metrics
        return None
    
    def _get_storage_bucket_last_used(self, bucket: Any) -> Optional[datetime]:
        """Get last used time for Storage bucket."""
        # This would require storage usage logs
        return None
    
    def _get_sql_instance_last_used(self, instance: Any) -> Optional[datetime]:
        """Get last used time for SQL instance."""
        # This would require SQL usage metrics
        return None
