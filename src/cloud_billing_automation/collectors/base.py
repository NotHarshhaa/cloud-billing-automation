"""
Base collector class for cloud billing data.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from ..core.exceptions import CollectorError


@dataclass
class BillingData:
    """Standardized billing data structure."""
    provider: str
    account_id: str
    service: str
    region: str
    resource_id: str
    resource_name: str
    usage_type: str
    usage_amount: float
    usage_unit: str
    cost: float
    currency: str
    start_time: datetime
    end_time: datetime
    tags: Dict[str, str]
    environment: Optional[str] = None
    cost_center: Optional[str] = None


@dataclass
class ResourceData:
    """Standardized resource data structure."""
    provider: str
    account_id: str
    resource_id: str
    resource_name: str
    resource_type: str
    region: str
    state: str
    creation_time: datetime
    tags: Dict[str, str]
    environment: Optional[str] = None
    cost_center: Optional[str] = None
    is_idle: bool = False
    last_used_time: Optional[datetime] = None


class BaseCollector(ABC):
    """Base class for cloud billing data collectors."""
    
    def __init__(self, config: Any, credentials: Dict[str, str]):
        self.config = config
        self.credentials = credentials
        self.provider_name = self.__class__.__name__.replace("Collector", "").lower()
    
    @abstractmethod
    def authenticate(self) -> None:
        """Authenticate with the cloud provider."""
        pass
    
    @abstractmethod
    def collect_billing_data(self, start_date: datetime, end_date: datetime) -> List[BillingData]:
        """Collect billing data for the specified date range."""
        pass
    
    @abstractmethod
    def collect_resource_data(self) -> List[ResourceData]:
        """Collect resource inventory data."""
        pass
    
    @abstractmethod
    def get_cost_breakdown(self, start_date: datetime, end_date: datetime, 
                          group_by: str = "service") -> Dict[str, float]:
        """Get cost breakdown by specified grouping."""
        pass
    
    def validate_date_range(self, start_date: datetime, end_date: datetime) -> None:
        """Validate the date range for data collection."""
        if start_date >= end_date:
            raise CollectorError("Start date must be before end date")
        
        if end_date > datetime.now():
            raise CollectorError("End date cannot be in the future")
        
        if (end_date - start_date) > timedelta(days=365):
            raise CollectorError("Date range cannot exceed 365 days")
    
    def filter_data_by_region(self, data: List[Any], regions: List[str]) -> List[Any]:
        """Filter data by specified regions."""
        if not regions:
            return data
        
        return [item for item in data if item.region in regions]
    
    def filter_data_by_tags(self, data: List[Any], 
                           required_tags: List[str]) -> List[Any]:
        """Filter data to only include items with required tags."""
        if not required_tags:
            return data
        
        filtered_data = []
        for item in data:
            if all(tag in item.tags for tag in required_tags):
                filtered_data.append(item)
        
        return filtered_data
    
    def extract_environment_from_tags(self, tags: Dict[str, str], 
                                    environment_tag: str) -> Optional[str]:
        """Extract environment from resource tags."""
        return tags.get(environment_tag)
    
    def extract_cost_center_from_tags(self, tags: Dict[str, str], 
                                    cost_center_tag: str) -> Optional[str]:
        """Extract cost center from resource tags."""
        return tags.get(cost_center_tag)
    
    def standardize_tags(self, raw_tags: Dict[str, Any]) -> Dict[str, str]:
        """Standardize tags to string key-value pairs."""
        standardized = {}
        for key, value in raw_tags.items():
            if value is not None:
                standardized[str(key)] = str(value)
        return standardized
    
    def calculate_daily_costs(self, billing_data: List[BillingData]) -> Dict[str, float]:
        """Calculate daily costs from billing data."""
        daily_costs = {}
        
        for data in billing_data:
            date_str = data.start_time.strftime("%Y-%m-%d")
            if date_str not in daily_costs:
                daily_costs[date_str] = 0.0
            daily_costs[date_str] += data.cost
        
        return daily_costs
    
    def get_top_services_by_cost(self, billing_data: List[BillingData], 
                               limit: int = 10) -> List[Dict[str, Any]]:
        """Get top services by cost."""
        service_costs = {}
        
        for data in billing_data:
            if data.service not in service_costs:
                service_costs[data.service] = 0.0
            service_costs[data.service] += data.cost
        
        # Sort by cost and return top N
        sorted_services = sorted(service_costs.items(), 
                               key=lambda x: x[1], reverse=True)
        
        return [
            {"service": service, "cost": cost}
            for service, cost in sorted_services[:limit]
        ]
    
    def get_cost_anomaly_candidates(self, billing_data: List[BillingData], 
                                  threshold_multiplier: float = 2.0) -> List[BillingData]:
        """Identify potential cost anomalies in billing data."""
        # Calculate average cost per service
        service_costs = {}
        service_counts = {}
        
        for data in billing_data:
            if data.service not in service_costs:
                service_costs[data.service] = 0.0
                service_counts[data.service] = 0
            service_costs[data.service] += data.cost
            service_counts[data.service] += 1
        
        # Calculate average cost per service
        service_avg_costs = {}
        for service, total_cost in service_costs.items():
            service_avg_costs[service] = total_cost / service_counts[service]
        
        # Find anomalies (costs significantly above average)
        anomalies = []
        for data in billing_data:
            avg_cost = service_avg_costs.get(data.service, 0)
            if avg_cost > 0 and data.cost > avg_cost * threshold_multiplier:
                anomalies.append(data)
        
        return anomalies
