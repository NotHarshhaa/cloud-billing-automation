"""
Cost anomaly detection for cloud billing data.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from ..collectors.base import BillingData
from ..core.exceptions import AnalyzerError


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""
    anomaly_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    resource_id: str
    service: str
    expected_value: float
    actual_value: float
    deviation_percentage: float
    date: datetime
    confidence_score: float
    recommendations: List[str]


@dataclass
class AnomalyPattern:
    """Pattern detected in anomalies."""
    pattern_type: str
    frequency: int
    affected_resources: List[str]
    time_period: str
    description: str


class AnomalyDetector:
    """Detects anomalies in cloud billing data using various statistical methods."""
    
    def __init__(self, config: Any):
        self.config = config
        self.z_score_threshold = 2.5
        self.iqr_multiplier = 1.5
        self.percentage_threshold = 50.0  # 50% deviation threshold
    
    def detect_anomalies(self, billing_data: List[BillingData], 
                        methods: List[str] = None) -> List[AnomalyResult]:
        """Detect anomalies using multiple methods."""
        if methods is None:
            methods = ["zscore", "iqr", "percentage"]
        
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for anomaly detection")
            
            # Convert to DataFrame
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            
            all_anomalies = []
            
            # Run different detection methods
            if "zscore" in methods:
                zscore_anomalies = self._detect_zscore_anomalies(df)
                all_anomalies.extend(zscore_anomalies)
            
            if "iqr" in methods:
                iqr_anomalies = self._detect_iqr_anomalies(df)
                all_anomalies.extend(iqr_anomalies)
            
            if "percentage" in methods:
                percentage_anomalies = self._detect_percentage_anomalies(df)
                all_anomalies.extend(percentage_anomalies)
            
            if "seasonal" in methods:
                seasonal_anomalies = self._detect_seasonal_anomalies(df)
                all_anomalies.extend(seasonal_anomalies)
            
            # Remove duplicates and merge results
            merged_anomalies = self._merge_anomaly_results(all_anomalies)
            
            # Sort by severity and confidence
            merged_anomalies.sort(key=lambda x: (self._severity_score(x.severity), x.confidence_score), 
                                reverse=True)
            
            return merged_anomalies
            
        except Exception as e:
            raise AnalyzerError(f"Failed to detect anomalies: {e}")
    
    def detect_anomaly_patterns(self, anomalies: List[AnomalyResult]) -> List[AnomalyPattern]:
        """Detect patterns in anomalies."""
        try:
            if not anomalies:
                return []
            
            patterns = []
            
            # Resource-specific patterns
            resource_patterns = self._detect_resource_patterns(anomalies)
            patterns.extend(resource_patterns)
            
            # Service-specific patterns
            service_patterns = self._detect_service_patterns(anomalies)
            patterns.extend(service_patterns)
            
            # Time-based patterns
            time_patterns = self._detect_time_patterns(anomalies)
            patterns.extend(time_patterns)
            
            # Cost escalation patterns
            escalation_patterns = self._detect_escalation_patterns(anomalies)
            patterns.extend(escalation_patterns)
            
            return patterns
            
        except Exception as e:
            raise AnalyzerError(f"Failed to detect anomaly patterns: {e}")
    
    def get_anomaly_summary(self, anomalies: List[AnomalyResult]) -> Dict[str, Any]:
        """Get summary statistics for detected anomalies."""
        try:
            if not anomalies:
                return {
                    "total_anomalies": 0,
                    "by_severity": {},
                    "by_type": {},
                    "by_service": {},
                    "by_resource": {},
                    "total_cost_impact": 0.0,
                    "high_confidence_anomalies": 0
                }
            
            # Count by severity
            severity_counts = {}
            for anomaly in anomalies:
                severity_counts[anomaly.severity] = severity_counts.get(anomaly.severity, 0) + 1
            
            # Count by type
            type_counts = {}
            for anomaly in anomalies:
                type_counts[anomaly.anomaly_type] = type_counts.get(anomaly.anomaly_type, 0) + 1
            
            # Count by service
            service_counts = {}
            for anomaly in anomalies:
                service_counts[anomaly.service] = service_counts.get(anomaly.service, 0) + 1
            
            # Count by resource
            resource_counts = {}
            for anomaly in anomalies:
                resource_counts[anomaly.resource_id] = resource_counts.get(anomaly.resource_id, 0) + 1
            
            # Calculate total cost impact
            total_cost_impact = sum(anomaly.actual_value - anomaly.expected_value 
                                  for anomaly in anomalies)
            
            # Count high confidence anomalies
            high_confidence_count = sum(1 for anomaly in anomalies 
                                     if anomaly.confidence_score >= 0.8)
            
            return {
                "total_anomalies": len(anomalies),
                "by_severity": severity_counts,
                "by_type": type_counts,
                "by_service": service_counts,
                "by_resource": resource_counts,
                "total_cost_impact": total_cost_impact,
                "high_confidence_anomalies": high_confidence_count
            }
            
        except Exception as e:
            raise AnalyzerError(f"Failed to generate anomaly summary: {e}")
    
    def _detect_zscore_anomalies(self, df: pd.DataFrame) -> List[AnomalyResult]:
        """Detect anomalies using Z-score method."""
        anomalies = []
        
        # Group by service and resource for more accurate detection
        for (service, resource_id), group in df.groupby(['service', 'resource_id']):
            if len(group) < 3:  # Need at least 3 data points
                continue
            
            costs = group['cost'].values
            mean_cost = np.mean(costs)
            std_cost = np.std(costs)
            
            if std_cost == 0:
                continue
            
            # Calculate Z-scores
            z_scores = np.abs((costs - mean_cost) / std_cost)
            
            for i, z_score in enumerate(z_scores):
                if z_score > self.z_score_threshold:
                    row = group.iloc[i]
                    severity = self._calculate_severity(z_score, "zscore")
                    confidence = min(1.0, z_score / 3.0)  # Normalize confidence
                    
                    anomaly = AnomalyResult(
                        anomaly_type="zscore_outlier",
                        severity=severity,
                        description=f"Cost spike detected using Z-score method",
                        resource_id=row['resource_id'],
                        service=row['service'],
                        expected_value=mean_cost,
                        actual_value=row['cost'],
                        deviation_percentage=((row['cost'] - mean_cost) / mean_cost * 100) if mean_cost > 0 else 0,
                        date=row['start_time'],
                        confidence_score=confidence,
                        recommendations=self._generate_zscore_recommendations(row, z_score)
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_iqr_anomalies(self, df: pd.DataFrame) -> List[AnomalyResult]:
        """Detect anomalies using Interquartile Range (IQR) method."""
        anomalies = []
        
        for (service, resource_id), group in df.groupby(['service', 'resource_id']):
            if len(group) < 4:  # Need at least 4 data points for IQR
                continue
            
            costs = group['cost'].values
            q1 = np.percentile(costs, 25)
            q3 = np.percentile(costs, 75)
            iqr = q3 - q1
            
            if iqr == 0:
                continue
            
            lower_bound = q1 - (self.iqr_multiplier * iqr)
            upper_bound = q3 + (self.iqr_multiplier * iqr)
            
            for i, cost in enumerate(costs):
                if cost < lower_bound or cost > upper_bound:
                    row = group.iloc[i]
                    
                    # Calculate severity based on distance from bounds
                    if cost > upper_bound:
                        distance = (cost - upper_bound) / iqr
                    else:
                        distance = (lower_bound - cost) / iqr
                    
                    severity = self._calculate_severity(distance, "iqr")
                    confidence = min(1.0, distance / 2.0)
                    
                    anomaly = AnomalyResult(
                        anomaly_type="iqr_outlier",
                        severity=severity,
                        description=f"Cost spike detected using IQR method",
                        resource_id=row['resource_id'],
                        service=row['service'],
                        expected_value=(q1 + q3) / 2,  # Use median as expected
                        actual_value=row['cost'],
                        deviation_percentage=((row['cost'] - ((q1 + q3) / 2)) / ((q1 + q3) / 2) * 100) if (q1 + q3) / 2 > 0 else 0,
                        date=row['start_time'],
                        confidence_score=confidence,
                        recommendations=self._generate_iqr_recommendations(row, distance)
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_percentage_anomalies(self, df: pd.DataFrame) -> List[AnomalyResult]:
        """Detect anomalies based on percentage deviation from historical average."""
        anomalies = []
        
        for (service, resource_id), group in df.groupby(['service', 'resource_id']):
            if len(group) < 2:
                continue
            
            # Calculate historical average (excluding current day)
            group_sorted = group.sort_values('start_time')
            
            for i in range(1, len(group_sorted)):
                current_row = group_sorted.iloc[i]
                historical_data = group_sorted.iloc[:i]
                
                historical_avg = historical_data['cost'].mean()
                
                if historical_avg == 0:
                    continue
                
                deviation_percentage = abs((current_row['cost'] - historical_avg) / historical_avg * 100)
                
                if deviation_percentage > self.percentage_threshold:
                    severity = self._calculate_severity(deviation_percentage / 10, "percentage")
                    confidence = min(1.0, deviation_percentage / 100)
                    
                    anomaly = AnomalyResult(
                        anomaly_type="percentage_deviation",
                        severity=severity,
                        description=f"Cost deviation of {deviation_percentage:.1f}% from historical average",
                        resource_id=current_row['resource_id'],
                        service=current_row['service'],
                        expected_value=historical_avg,
                        actual_value=current_row['cost'],
                        deviation_percentage=deviation_percentage,
                        date=current_row['start_time'],
                        confidence_score=confidence,
                        recommendations=self._generate_percentage_recommendations(current_row, deviation_percentage)
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_seasonal_anomalies(self, df: pd.DataFrame) -> List[AnomalyResult]:
        """Detect seasonal anomalies (e.g., weekend vs weekday patterns)."""
        anomalies = []
        
        # Add day of week
        df['day_of_week'] = df['start_time'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6])
        
        for (service, resource_id), group in df.groupby(['service', 'resource_id']):
            if len(group) < 14:  # Need at least 2 weeks of data
                continue
            
            # Compare weekend vs weekday costs
            weekend_costs = group[group['is_weekend']]['cost']
            weekday_costs = group[~group['is_weekend']]['cost']
            
            if len(weekend_costs) == 0 or len(weekday_costs) == 0:
                continue
            
            weekend_avg = weekend_costs.mean()
            weekday_avg = weekday_costs.mean()
            
            # Check for unusual weekend activity
            for _, row in weekend_costs.items():
                cost = row
                if weekday_avg > 0 and (cost / weekday_avg) > 2.0:  # Weekend cost 2x weekday average
                    original_row = group[group['cost'] == cost].iloc[0]
                    
                    anomaly = AnomalyResult(
                        anomaly_type="seasonal_anomaly",
                        severity="medium",
                        description="Unusual weekend cost spike detected",
                        resource_id=original_row['resource_id'],
                        service=original_row['service'],
                        expected_value=weekday_avg,
                        actual_value=cost,
                        deviation_percentage=((cost - weekday_avg) / weekday_avg * 100),
                        date=original_row['start_time'],
                        confidence_score=0.7,
                        recommendations=["Review weekend resource usage", "Consider implementing weekend shutdown policies"]
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_resource_patterns(self, anomalies: List[AnomalyResult]) -> List[AnomalyPattern]:
        """Detect patterns related to specific resources."""
        patterns = []
        
        # Resources with multiple anomalies
        resource_counts = {}
        for anomaly in anomalies:
            resource_counts[anomaly.resource_id] = resource_counts.get(anomaly.resource_id, 0) + 1
        
        frequent_offenders = {k: v for k, v in resource_counts.items() if v >= 3}
        
        if frequent_offenders:
            pattern = AnomalyPattern(
                pattern_type="repeated_resource_anomalies",
                frequency=len(frequent_offenders),
                affected_resources=list(frequent_offenders.keys()),
                time_period="last 30 days",
                description=f"Found {len(frequent_offenders)} resources with 3+ anomalies"
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_service_patterns(self, anomalies: List[AnomalyResult]) -> List[AnomalyPattern]:
        """Detect patterns related to specific services."""
        patterns = []
        
        # Services with multiple anomalies
        service_counts = {}
        for anomaly in anomalies:
            service_counts[anomaly.service] = service_counts.get(anomaly.service, 0) + 1
        
        problematic_services = {k: v for k, v in service_counts.items() if v >= 5}
        
        if problematic_services:
            pattern = AnomalyPattern(
                pattern_type="service_anomaly_cluster",
                frequency=len(problematic_services),
                affected_resources=list(problematic_services.keys()),
                time_period="last 30 days",
                description=f"Found {len(problematic_services)} services with 5+ anomalies"
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_time_patterns(self, anomalies: List[AnomalyResult]) -> List[AnomalyPattern]:
        """Detect time-based patterns in anomalies."""
        patterns = []
        
        # Group anomalies by hour of day
        hour_counts = {}
        for anomaly in anomalies:
            hour = anomaly.date.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        peak_hours = {k: v for k, v in hour_counts.items() if v >= 3}
        
        if peak_hours:
            pattern = AnomalyPattern(
                pattern_type="time_based_anomaly_cluster",
                frequency=len(peak_hours),
                affected_resources=[f"Hour {h}" for h in peak_hours.keys()],
                time_period="last 30 days",
                description=f"Anomalies frequently occur during hours: {list(peak_hours.keys())}"
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_escalation_patterns(self, anomalies: List[AnomalyResult]) -> List[AnomalyPattern]:
        """Detect cost escalation patterns."""
        patterns = []
        
        # Look for increasing cost anomalies over time
        resource_anomalies = {}
        for anomaly in anomalies:
            if anomaly.resource_id not in resource_anomalies:
                resource_anomalies[anomaly.resource_id] = []
            resource_anomalies[anomaly.resource_id].append(anomaly)
        
        escalating_resources = []
        for resource_id, resource_anomaly_list in resource_anomalies.items():
            if len(resource_anomaly_list) >= 3:
                # Sort by date
                sorted_anomalies = sorted(resource_anomaly_list, key=lambda x: x.date)
                
                # Check if costs are generally increasing
                costs = [a.actual_value for a in sorted_anomalies]
                if all(costs[i] <= costs[i+1] for i in range(len(costs)-1)):
                    escalating_resources.append(resource_id)
        
        if escalating_resources:
            pattern = AnomalyPattern(
                pattern_type="cost_escalation",
                frequency=len(escalating_resources),
                affected_resources=escalating_resources,
                time_period="last 30 days",
                description=f"Found {len(escalating_resources)} resources with escalating costs"
            )
            patterns.append(pattern)
        
        return patterns
    
    def _merge_anomaly_results(self, anomalies: List[AnomalyResult]) -> List[AnomalyResult]:
        """Merge duplicate anomaly results."""
        # Simple merging based on resource_id and date
        merged = {}
        
        for anomaly in anomalies:
            key = (anomaly.resource_id, anomaly.date.date())
            
            if key in merged:
                # Keep the anomaly with higher confidence
                if anomaly.confidence_score > merged[key].confidence_score:
                    merged[key] = anomaly
            else:
                merged[key] = anomaly
        
        return list(merged.values())
    
    def _calculate_severity(self, score: float, method: str) -> str:
        """Calculate severity based on anomaly score."""
        if method == "zscore":
            if score > 4:
                return "critical"
            elif score > 3:
                return "high"
            elif score > 2.5:
                return "medium"
            else:
                return "low"
        elif method == "iqr":
            if score > 3:
                return "critical"
            elif score > 2:
                return "high"
            elif score > 1.5:
                return "medium"
            else:
                return "low"
        elif method == "percentage":
            if score > 20:
                return "critical"
            elif score > 10:
                return "high"
            elif score > 5:
                return "medium"
            else:
                return "low"
        else:
            return "medium"
    
    def _severity_score(self, severity: str) -> int:
        """Convert severity to numeric score for sorting."""
        severity_scores = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return severity_scores.get(severity, 0)
    
    def _generate_zscore_recommendations(self, row: pd.Series, z_score: float) -> List[str]:
        """Generate recommendations for Z-score anomalies."""
        recommendations = []
        
        if z_score > 4:
            recommendations.append("Critical cost spike detected - immediate investigation required")
            recommendations.append("Consider implementing cost alerts for this resource")
        elif z_score > 3:
            recommendations.append("Significant cost variation detected")
            recommendations.append("Review resource configuration and usage patterns")
        else:
            recommendations.append("Monitor this resource for continued anomalies")
        
        return recommendations
    
    def _generate_iqr_recommendations(self, row: pd.Series, distance: float) -> List[str]:
        """Generate recommendations for IQR anomalies."""
        recommendations = []
        
        if distance > 3:
            recommendations.append("Extreme cost outlier detected")
            recommendations.append("Verify if this cost is legitimate or due to error")
        elif distance > 2:
            recommendations.append("Cost outside normal range detected")
            recommendations.append("Consider setting up budget alerts")
        
        return recommendations
    
    def _generate_percentage_recommendations(self, row: pd.Series, deviation: float) -> List[str]:
        """Generate recommendations for percentage anomalies."""
        recommendations = []
        
        if deviation > 100:
            recommendations.append("Cost doubled compared to historical average")
            recommendations.append("Check for resource misconfiguration or unexpected usage")
        elif deviation > 50:
            recommendations.append("Significant cost increase detected")
            recommendations.append("Review recent changes to this resource")
        
        return recommendations
    
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
