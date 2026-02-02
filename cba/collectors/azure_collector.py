"""
Azure billing data collector.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from azure.identity import ClientSecretCredential
from azure.mgmt.billing import BillingManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.web import WebSiteManagementClient
from .base import BaseCollector, BillingData, ResourceData
from ..core.exceptions import CollectorError, APIError


class AzureCollector(BaseCollector):
    """Azure billing data collector using Azure Management APIs."""
    
    def __init__(self, config: Any, credentials: Dict[str, str]):
        super().__init__(config, credentials)
        self.credential = None
        self.billing_client = None
        self.resource_client = None
        self.compute_client = None
        self.sql_client = None
        self.storage_client = None
        self.web_client = None
    
    def authenticate(self) -> None:
        """Authenticate with Azure using service principal credentials."""
        try:
            self.credential = ClientSecretCredential(
                tenant_id=self.credentials["tenant_id"],
                client_id=self.credentials["client_id"],
                client_secret=self.credentials["client_secret"]
            )
            
            # Initialize clients
            self.billing_client = BillingManagementClient(
                self.credential, 
                self.credentials["subscription_id"]
            )
            self.resource_client = ResourceManagementClient(
                self.credential, 
                self.credentials["subscription_id"]
            )
            self.compute_client = ComputeManagementClient(
                self.credential, 
                self.credentials["subscription_id"]
            )
            self.sql_client = SqlManagementClient(
                self.credential, 
                self.credentials["subscription_id"]
            )
            self.storage_client = StorageManagementClient(
                self.credential, 
                self.credentials["subscription_id"]
            )
            self.web_client = WebSiteManagementClient(
                self.credential, 
                self.credentials["subscription_id"]
            )
            
            # Test authentication
            self.resource_client.resource_groups.list()
            
        except Exception as e:
            raise APIError(f"Azure authentication failed: {e}")
    
    def collect_billing_data(self, start_date: datetime, end_date: datetime) -> List[BillingData]:
        """Collect Azure billing data using Billing Management API."""
        self.validate_date_range(start_date, end_date)
        
        try:
            billing_data = []
            
            # Get billing account info
            billing_accounts = list(self.billing_client.billing_accounts.list())
            
            for billing_account in billing_accounts:
                # Get billing periods
                billing_periods = list(self.billing_client.billing_periods.list_by_billing_account(
                    billing_account_name=billing_account.name
                ))
                
                for period in billing_periods:
                    period_start = period.billing_period_start_date.date()
                    period_end = period.billing_period_end_date.date()
                    
                    # Check if period overlaps with requested date range
                    if not (period_end < start_date.date() or period_start > end_date.date()):
                        # Get usage details for this period
                        usage_details = self._get_usage_details(
                            billing_account.name, 
                            period_start, 
                            period_end
                        )
                        
                        billing_data.extend(usage_details)
            
            return billing_data
            
        except Exception as e:
            raise CollectorError(f"Failed to collect Azure billing data: {e}")
    
    def collect_resource_data(self) -> List[ResourceData]:
        """Collect Azure resource inventory data."""
        try:
            resources = []
            
            # Collect VMs
            resources.extend(self._collect_virtual_machines())
            
            # Collect SQL databases
            resources.extend(self._collect_sql_databases())
            
            # Collect storage accounts
            resources.extend(self._collect_storage_accounts())
            
            # Collect App Services
            resources.extend(self._collect_app_services())
            
            return resources
            
        except Exception as e:
            raise CollectorError(f"Failed to collect Azure resource data: {e}")
    
    def get_cost_breakdown(self, start_date: datetime, end_date: datetime, 
                          group_by: str = "service") -> Dict[str, float]:
        """Get Azure cost breakdown by specified grouping."""
        self.validate_date_range(start_date, end_date)
        
        try:
            # Get cost management data
            cost_data = self._get_cost_management_data(start_date, end_date)
            
            cost_breakdown = {}
            
            for item in cost_data:
                key = self._get_grouping_key(item, group_by)
                cost = float(item.get('amount', 0))
                
                if key not in cost_breakdown:
                    cost_breakdown[key] = 0.0
                cost_breakdown[key] += cost
            
            return cost_breakdown
            
        except Exception as e:
            raise CollectorError(f"Failed to get Azure cost breakdown: {e}")
    
    def _get_usage_details(self, billing_account_name: str, 
                          start_date: datetime.date, end_date: datetime.date) -> List[BillingData]:
        """Get usage details for a billing period."""
        usage_data = []
        
        try:
            # This is a simplified implementation
            # In practice, you'd use the Azure Consumption Management API
            # or Azure Cost Management API for detailed usage data
            
            # For now, we'll create a placeholder implementation
            # that would be replaced with actual API calls
            
            return usage_data
            
        except Exception as e:
            raise CollectorError(f"Failed to get usage details: {e}")
    
    def _get_cost_management_data(self, start_date: datetime, 
                                 end_date: datetime) -> List[Dict[str, Any]]:
        """Get cost management data for analysis."""
        try:
            # This would use Azure Cost Management API
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            raise CollectorError(f"Failed to get cost management data: {e}")
    
    def _get_grouping_key(self, item: Dict[str, Any], group_by: str) -> str:
        """Get grouping key for cost breakdown."""
        if group_by == "service":
            return item.get('service_name', 'Unknown')
        elif group_by == "region":
            return item.get('resource_location', 'Unknown')
        elif group_by == "resource_type":
            return item.get('resource_type', 'Unknown')
        else:
            return 'Unknown'
    
    def _collect_virtual_machines(self) -> List[ResourceData]:
        """Collect Azure VM data."""
        resources = []
        
        try:
            for vm in self.compute_client.virtual_machines.list_all():
                # Get VM tags
                tags = self.standardize_tags(vm.tags or {})
                
                # Get resource group name
                resource_group = self._extract_resource_group(vm.id)
                
                resource = ResourceData(
                    provider="azure",
                    account_id=self.config.azure.subscription_id,
                    resource_id=vm.id,
                    resource_name=vm.name,
                    resource_type="Virtual Machine",
                    region=vm.location,
                    state=vm.provisioning_state,
                    creation_time=self._get_resource_creation_time(vm.id),
                    tags=tags,
                    environment=self.extract_environment_from_tags(
                        tags, self.config.azure.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        tags, self.config.azure.cost_center_tag
                    ),
                    is_idle=self._is_vm_idle(vm),
                    last_used_time=self._get_vm_last_used(vm)
                )
                
                resources.append(resource)
                
        except Exception as e:
            raise CollectorError(f"Failed to collect Azure VMs: {e}")
        
        return resources
    
    def _collect_sql_databases(self) -> List[ResourceData]:
        """Collect Azure SQL database data."""
        resources = []
        
        try:
            for db in self.sql_client.databases.list_by_server(
                resource_group_name="",  # Would need to iterate through resource groups
                server_name=""
            ):
                tags = self.standardize_tags(db.tags or {})
                
                resource = ResourceData(
                    provider="azure",
                    account_id=self.config.azure.subscription_id,
                    resource_id=db.id,
                    resource_name=db.name,
                    resource_type="SQL Database",
                    region=db.location,
                    state=db.status,
                    creation_time=self._get_resource_creation_time(db.id),
                    tags=tags,
                    environment=self.extract_environment_from_tags(
                        tags, self.config.azure.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        tags, self.config.azure.cost_center_tag
                    ),
                    is_idle=self._is_sql_idle(db),
                    last_used_time=None
                )
                
                resources.append(resource)
                
        except Exception as e:
            raise CollectorError(f"Failed to collect Azure SQL databases: {e}")
        
        return resources
    
    def _collect_storage_accounts(self) -> List[ResourceData]:
        """Collect Azure Storage account data."""
        resources = []
        
        try:
            for storage in self.storage_client.storage_accounts.list():
                tags = self.standardize_tags(storage.tags or {})
                
                resource = ResourceData(
                    provider="azure",
                    account_id=self.config.azure.subscription_id,
                    resource_id=storage.id,
                    resource_name=storage.name,
                    resource_type="Storage Account",
                    region=storage.location,
                    state=storage.provisioning_state,
                    creation_time=storage.creation_time,
                    tags=tags,
                    environment=self.extract_environment_from_tags(
                        tags, self.config.azure.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        tags, self.config.azure.cost_center_tag
                    ),
                    is_idle=self._is_storage_idle(storage),
                    last_used_time=self._get_storage_last_used(storage)
                )
                
                resources.append(resource)
                
        except Exception as e:
            raise CollectorError(f"Failed to collect Azure Storage accounts: {e}")
        
        return resources
    
    def _collect_app_services(self) -> List[ResourceData]:
        """Collect Azure App Service data."""
        resources = []
        
        try:
            for app in self.web_client.web_apps.list():
                tags = self.standardize_tags(app.tags or {})
                
                resource = ResourceData(
                    provider="azure",
                    account_id=self.config.azure.subscription_id,
                    resource_id=app.id,
                    resource_name=app.name,
                    resource_type="App Service",
                    region=app.location,
                    state=app.state,
                    creation_time=self._get_resource_creation_time(app.id),
                    tags=tags,
                    environment=self.extract_environment_from_tags(
                        tags, self.config.azure.environment_tag
                    ),
                    cost_center=self.extract_cost_center_from_tags(
                        tags, self.config.azure.cost_center_tag
                    ),
                    is_idle=self._is_app_service_idle(app),
                    last_used_time=self._get_app_service_last_used(app)
                )
                
                resources.append(resource)
                
        except Exception as e:
            raise CollectorError(f"Failed to collect Azure App Services: {e}")
        
        return resources
    
    def _extract_resource_group(self, resource_id: str) -> str:
        """Extract resource group name from resource ID."""
        try:
            parts = resource_id.split('/')
            return parts[parts.index('resourceGroups') + 1]
        except (ValueError, IndexError):
            return "Unknown"
    
    def _get_resource_creation_time(self, resource_id: str) -> datetime:
        """Get resource creation time."""
        try:
            # This would use Azure Resource Graph or Resource Manager API
            # For now, return current time as placeholder
            return datetime.now()
        except Exception:
            return datetime.now()
    
    def _is_vm_idle(self, vm: Any) -> bool:
        """Determine if VM is idle."""
        # Check VM power state and metrics
        # This is a simplified implementation
        return vm.provisioning_state.lower() != 'succeeded'
    
    def _is_sql_idle(self, db: Any) -> bool:
        """Determine if SQL database is idle."""
        # Check database status and metrics
        return db.status.lower() != 'online'
    
    def _is_storage_idle(self, storage: Any) -> bool:
        """Determine if storage account is idle."""
        # Check storage metrics
        return False  # Would need metrics analysis
    
    def _is_app_service_idle(self, app: Any) -> bool:
        """Determine if App Service is idle."""
        # Check app state and metrics
        return app.state.lower() != 'running'
    
    def _get_vm_last_used(self, vm: Any) -> Optional[datetime]:
        """Get last used time for VM."""
        # This would require Azure Monitor metrics
        return None
    
    def _get_storage_last_used(self, storage: Any) -> Optional[datetime]:
        """Get last used time for storage account."""
        # This would require storage metrics
        return None
    
    def _get_app_service_last_used(self, app: Any) -> Optional[datetime]:
        """Get last used time for App Service."""
        # This would require App Service metrics
        return None
