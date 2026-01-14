"""
Cost analysis and breakdown functionality.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from ..collectors.base import BillingData, ResourceData
from ..core.exceptions import AnalyzerError


@dataclass
class CostSummary:
    """Cost summary for a time period."""
    total_cost: float
    currency: str
    period_start: datetime
    period_end: datetime
    cost_by_service: Dict[str, float]
    cost_by_region: Dict[str, float]
    cost_by_environment: Dict[str, float]
    cost_by_cost_center: Dict[str, float]
    daily_costs: Dict[str, float]
    top_resources: List[Dict[str, Any]]


@dataclass
class CostTrend:
    """Cost trend analysis."""
    period: str
    current_cost: float
    previous_cost: float
    change_amount: float
    change_percentage: float
    trend_direction: str  # "up", "down", "stable"


@dataclass
class ResourceCostAnalysis:
    """Resource-level cost analysis."""
    resource_id: str
    resource_name: str
    resource_type: str
    total_cost: float
    daily_average_cost: float
    cost_trend: str
    efficiency_score: float
    recommendations: List[str]


class CostAnalyzer:
    """Analyzes cloud billing data to provide insights and breakdowns."""
    
    def __init__(self, config: Any):
        self.config = config
    
    def analyze_costs(self, billing_data: List[BillingData], 
                      start_date: datetime, end_date: datetime) -> CostSummary:
        """Perform comprehensive cost analysis."""
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for analysis")
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            
            # Calculate total cost
            total_cost = df['cost'].sum()
            currency = df['currency'].iloc[0] if not df.empty else 'USD'
            
            # Cost breakdowns
            cost_by_service = df.groupby('service')['cost'].sum().to_dict()
            cost_by_region = df.groupby('region')['cost'].sum().to_dict()
            cost_by_environment = df.groupby('environment')['cost'].sum().to_dict()
            cost_by_cost_center = df.groupby('cost_center')['cost'].sum().to_dict()
            
            # Daily costs
            daily_costs = df.groupby(df['start_time'].dt.strftime('%Y-%m-%d'))['cost'].sum().to_dict()
            
            # Top resources by cost
            top_resources = self._get_top_resources_by_cost(df)
            
            return CostSummary(
                total_cost=total_cost,
                currency=currency,
                period_start=start_date,
                period_end=end_date,
                cost_by_service=cost_by_service,
                cost_by_region=cost_by_region,
                cost_by_environment=cost_by_environment,
                cost_by_cost_center=cost_by_cost_center,
                daily_costs=daily_costs,
                top_resources=top_resources
            )
            
        except Exception as e:
            raise AnalyzerError(f"Failed to analyze costs: {e}")
    
    def analyze_cost_trends(self, billing_data: List[BillingData], 
                           period: str = "monthly") -> List[CostTrend]:
        """Analyze cost trends over time."""
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for trend analysis")
            
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            
            # Group by period
            if period == "daily":
                df['period'] = df['start_time'].dt.strftime('%Y-%m-%d')
            elif period == "weekly":
                df['period'] = df['start_time'].dt.to_period('W').dt.start_time.dt.strftime('%Y-%m-%d')
            elif period == "monthly":
                df['period'] = df['start_time'].dt.to_period('M').dt.start_time.dt.strftime('%Y-%m-%d')
            else:
                raise AnalyzerError(f"Unsupported period: {period}")
            
            # Calculate costs per period
            period_costs = df.groupby('period')['cost'].sum().sort_index()
            
            # Calculate trends
            trends = []
            for i in range(1, len(period_costs)):
                current_cost = period_costs.iloc[i]
                previous_cost = period_costs.iloc[i-1]
                
                change_amount = current_cost - previous_cost
                change_percentage = (change_amount / previous_cost * 100) if previous_cost > 0 else 0
                
                if change_percentage > 5:
                    trend_direction = "up"
                elif change_percentage < -5:
                    trend_direction = "down"
                else:
                    trend_direction = "stable"
                
                trend = CostTrend(
                    period=period_costs.index[i],
                    current_cost=current_cost,
                    previous_cost=previous_cost,
                    change_amount=change_amount,
                    change_percentage=change_percentage,
                    trend_direction=trend_direction
                )
                trends.append(trend)
            
            return trends
            
        except Exception as e:
            raise AnalyzerError(f"Failed to analyze cost trends: {e}")
    
    def analyze_resource_costs(self, billing_data: List[BillingData], 
                             resource_data: List[ResourceData]) -> List[ResourceCostAnalysis]:
        """Analyze costs at the resource level."""
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for resource analysis")
            
            df_billing = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            
            # Group by resource
            resource_costs = df_billing.groupby('resource_id').agg({
                'cost': 'sum',
                'resource_name': 'first',
                'resource_type': 'first',
                'start_time': ['min', 'max']
            }).reset_index()
            
            # Flatten column names
            resource_costs.columns = ['resource_id', 'total_cost', 'resource_name', 
                                     'resource_type', 'first_seen', 'last_seen']
            
            # Calculate daily average
            resource_costs['days_active'] = (resource_costs['last_seen'] - resource_costs['first_seen']).dt.days + 1
            resource_costs['daily_average_cost'] = resource_costs['total_cost'] / resource_costs['days_active']
            
            # Analyze each resource
            analyses = []
            for _, row in resource_costs.iterrows():
                resource_id = row['resource_id']
                
                # Get cost trend for this resource
                resource_df = df_billing[df_billing['resource_id'] == resource_id]
                cost_trend = self._calculate_resource_cost_trend(resource_df)
                
                # Calculate efficiency score
                efficiency_score = self._calculate_efficiency_score(row, resource_df)
                
                # Generate recommendations
                recommendations = self._generate_resource_recommendations(row, resource_df)
                
                analysis = ResourceCostAnalysis(
                    resource_id=resource_id,
                    resource_name=row['resource_name'],
                    resource_type=row['resource_type'],
                    total_cost=row['total_cost'],
                    daily_average_cost=row['daily_average_cost'],
                    cost_trend=cost_trend,
                    efficiency_score=efficiency_score,
                    recommendations=recommendations
                )
                analyses.append(analysis)
            
            return analyses
            
        except Exception as e:
            raise AnalyzerError(f"Failed to analyze resource costs: {e}")
    
    def get_cost_forecast(self, billing_data: List[BillingData], 
                         forecast_days: int = 30) -> Dict[str, Any]:
        """Generate cost forecast based on historical data."""
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for forecasting")
            
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            
            # Group by day
            daily_costs = df.groupby(df['start_time'].dt.date)['cost'].sum()
            
            if len(daily_costs) < 7:
                raise AnalyzerError("Insufficient data for forecasting (need at least 7 days)")
            
            # Simple linear regression forecast
            X = np.arange(len(daily_costs)).reshape(-1, 1)
            y = daily_costs.values
            
            # Calculate trend
            coeffs = np.polyfit(X.flatten(), y, 1)
            slope = coeffs[0]
            intercept = coeffs[1]
            
            # Generate forecast
            forecast_values = []
            for i in range(forecast_days):
                future_x = len(daily_costs) + i
                forecast_value = slope * future_x + intercept
                forecast_values.append(max(0, forecast_value))  # Ensure non-negative
            
            # Calculate confidence intervals (simplified)
            residuals = y - (slope * X.flatten() + intercept)
            std_error = np.std(residuals)
            
            forecast_dates = [
                (daily_costs.index[-1] + timedelta(days=i+1)).strftime('%Y-%m-%d')
                for i in range(forecast_days)
            ]
            
            return {
                'forecast_dates': forecast_dates,
                'forecast_values': forecast_values.tolist(),
                'trend_slope': slope,
                'confidence_interval': std_error,
                'method': 'linear_regression',
                'total_forecast_cost': sum(forecast_values)
            }
            
        except Exception as e:
            raise AnalyzerError(f"Failed to generate cost forecast: {e}")
    
    def identify_cost_anomalies(self, billing_data: List[BillingData], 
                               threshold_multiplier: float = 2.0) -> List[Dict[str, Any]]:
        """Identify cost anomalies in billing data."""
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for anomaly detection")
            
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            
            anomalies = []
            
            # Check for anomalies by service
            service_stats = df.groupby('service')['cost'].agg(['mean', 'std']).reset_index()
            
            for _, service_stat in service_stats.iterrows():
                service = service_stat['service']
                mean_cost = service_stat['mean']
                std_cost = service_stat['std']
                
                if std_cost > 0:
                    threshold = mean_cost + (threshold_multiplier * std_cost)
                    
                    service_anomalies = df[
                        (df['service'] == service) & (df['cost'] > threshold)
                    ]
                    
                    for _, anomaly in service_anomalies.iterrows():
                        anomalies.append({
                            'type': 'service_anomaly',
                            'service': service,
                            'resource_id': anomaly['resource_id'],
                            'cost': anomaly['cost'],
                            'expected_cost': mean_cost,
                            'deviation': anomaly['cost'] - mean_cost,
                            'date': anomaly['start_time'].strftime('%Y-%m-%d')
                        })
            
            # Check for anomalies by resource
            resource_stats = df.groupby('resource_id')['cost'].agg(['mean', 'std']).reset_index()
            
            for _, resource_stat in resource_stats.iterrows():
                resource_id = resource_stat['resource_id']
                mean_cost = resource_stat['mean']
                std_cost = resource_stat['std']
                
                if std_cost > 0:
                    threshold = mean_cost + (threshold_multiplier * std_cost)
                    
                    resource_anomalies = df[
                        (df['resource_id'] == resource_id) & (df['cost'] > threshold)
                    ]
                    
                    for _, anomaly in resource_anomalies.iterrows():
                        anomalies.append({
                            'type': 'resource_anomaly',
                            'resource_id': resource_id,
                            'service': anomaly['service'],
                            'cost': anomaly['cost'],
                            'expected_cost': mean_cost,
                            'deviation': anomaly['cost'] - mean_cost,
                            'date': anomaly['start_time'].strftime('%Y-%m-%d')
                        })
            
            return anomalies
            
        except Exception as e:
            raise AnalyzerError(f"Failed to identify cost anomalies: {e}")
    
    def _billing_data_to_dict(self, data: BillingData) -> Dict[str, Any]:
        """Convert BillingData to dictionary."""
        return {
            'provider': data.provider,
            'account_id': data.account_id,
            'service': data.service,
            'region': data.region,
            'resource_id': data.resource_id,
            'resource_name': data.resource_name,
            'usage_type': data.usage_type,
            'usage_amount': data.usage_amount,
            'usage_unit': data.usage_unit,
            'cost': data.cost,
            'currency': data.currency,
            'start_time': data.start_time,
            'end_time': data.end_time,
            'tags': data.tags,
            'environment': data.environment,
            'cost_center': data.cost_center
        }
    
    def _get_top_resources_by_cost(self, df: pd.DataFrame, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top resources by cost."""
        resource_costs = df.groupby(['resource_id', 'resource_name', 'resource_type'])['cost'].sum()
        top_resources = resource_costs.nlargest(limit).reset_index()
        
        return [
            {
                'resource_id': row['resource_id'],
                'resource_name': row['resource_name'],
                'resource_type': row['resource_type'],
                'total_cost': row['cost']
            }
            for _, row in top_resources.iterrows()
        ]
    
    def _calculate_resource_cost_trend(self, resource_df: pd.DataFrame) -> str:
        """Calculate cost trend for a specific resource."""
        if len(resource_df) < 2:
            return "insufficient_data"
        
        # Sort by date
        resource_df = resource_df.sort_values('start_time')
        
        # Calculate trend
        costs = resource_df['cost'].values
        if len(costs) >= 3:
            # Simple trend calculation
            recent_avg = np.mean(costs[-3:])
            earlier_avg = np.mean(costs[:3]) if len(costs) >= 6 else np.mean(costs[:len(costs)//2])
            
            change_pct = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg > 0 else 0
            
            if change_pct > 10:
                return "increasing"
            elif change_pct < -10:
                return "decreasing"
            else:
                return "stable"
        else:
            return "insufficient_data"
    
    def _calculate_efficiency_score(self, resource_row: pd.Series, 
                                   resource_df: pd.DataFrame) -> float:
        """Calculate efficiency score for a resource."""
        # Simple efficiency calculation based on cost consistency
        costs = resource_df['cost'].values
        
        if len(costs) < 2:
            return 0.5  # Neutral score for insufficient data
        
        # Calculate coefficient of variation (lower is more consistent/efficient)
        cv = np.std(costs) / np.mean(costs) if np.mean(costs) > 0 else float('inf')
        
        # Convert to efficiency score (0-1, higher is better)
        efficiency_score = max(0, min(1, 1 - (cv / 2)))  # Normalize CV to 0-1 range
        
        return efficiency_score
    
    def _generate_resource_recommendations(self, resource_row: pd.Series, 
                                         resource_df: pd.DataFrame) -> List[str]:
        """Generate cost optimization recommendations for a resource."""
        recommendations = []
        
        # High cost recommendations
        if resource_row['total_cost'] > 1000:  # Arbitrary threshold
            recommendations.append("Consider reviewing resource sizing and utilization")
        
        # Low efficiency recommendations
        if resource_row['daily_average_cost'] > 50:
            recommendations.append("High daily cost detected - consider rightsizing or scheduling")
        
        # Trend-based recommendations
        costs = resource_df['cost'].values
        if len(costs) >= 7:
            recent_avg = np.mean(costs[-7:])
            earlier_avg = np.mean(costs[:-7]) if len(costs) > 7 else recent_avg
            
            if recent_avg > earlier_avg * 1.2:
                recommendations.append("Cost trend is increasing - investigate usage patterns")
        
        # Resource type specific recommendations
        resource_type = resource_row['resource_type'].lower()
        if 'ec2' in resource_type or 'vm' in resource_type or 'instance' in resource_type:
            recommendations.append("Consider using instance scheduling for non-production workloads")
        elif 'storage' in resource_type:
            recommendations.append("Review storage lifecycle policies and cleanup unused data")
        
        return recommendations
