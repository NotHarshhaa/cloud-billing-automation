"""
Anomaly alert management system.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from ..core.exceptions import AlertError
from ..analyzers.anomaly import AnomalyResult
from .base import BaseAlertManager, Alert, AlertRule, AlertSeverity, AlertStatus
from .channels import ChannelManager


class AnomalyAlertManager(BaseAlertManager):
    """Manages anomaly-related alerts."""
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.channel_manager = ChannelManager(config.get('notifications', {}))
        self.template_manager = self._create_template_manager()
        self.anomaly_history: List[Dict[str, Any]] = []
        self.suppression_rules = {}
        
        # Initialize default anomaly rules
        self._initialize_default_rules()
    
    def evaluate_conditions(self, anomalies: List[AnomalyResult]) -> List[Alert]:
        """Evaluate anomaly conditions and generate alerts."""
        alerts = []
        
        try:
            # Filter anomalies based on configuration
            filtered_anomalies = self._filter_anomalies(anomalies)
            
            # Group anomalies by resource and service
            grouped_anomalies = self._group_anomalies(filtered_anomalies)
            
            # Generate alerts for each group
            for group_key, anomaly_group in grouped_anomalies.items():
                alert = self._create_anomaly_alert(group_key, anomaly_group)
                if alert:
                    alerts.append(alert)
                    self.send_alert(alert)
            
            # Store anomalies in history
            self._store_anomaly_history(filtered_anomalies)
            
            return alerts
            
        except Exception as e:
            raise AlertError(f"Failed to evaluate anomaly conditions: {e}")
    
    def send_alert(self, alert: Alert) -> bool:
        """Send anomaly alert through configured channels."""
        try:
            # Prepare template data
            template_data = self._prepare_anomaly_template_data(alert)
            
            # Send through all enabled channels
            results = self.channel_manager.send_alert(alert, template_data)
            
            # Log results
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            if success_count == 0:
                print(f"Failed to send alert {alert.id} through any channel")
                return False
            elif success_count < total_count:
                print(f"Alert {alert.id} sent through {success_count}/{total_count} channels")
            
            return True
            
        except Exception as e:
            raise AlertError(f"Failed to send anomaly alert: {e}")
    
    def _filter_anomalies(self, anomalies: List[AnomalyResult]) -> List[AnomalyResult]:
        """Filter anomalies based on configuration."""
        filtered = []
        
        for anomaly in anomalies:
            # Filter by minimum confidence
            min_confidence = self.config.get('anomaly_detection', {}).get('min_confidence', 0.7)
            if anomaly.confidence_score < min_confidence:
                continue
            
            # Filter by minimum deviation
            min_deviation = self.config.get('anomaly_detection', {}).get('min_deviation_percentage', 20.0)
            if anomaly.deviation_percentage < min_deviation:
                continue
            
            # Check if anomaly is suppressed
            if self._is_anomaly_suppressed(anomaly):
                continue
            
            # Check if similar anomaly was recently sent
            if self._is_recent_anomaly(anomaly):
                continue
            
            filtered.append(anomaly)
        
        return filtered
    
    def _group_anomalies(self, anomalies: List[AnomalyResult]) -> Dict[str, List[AnomalyResult]]:
        """Group anomalies by resource and service."""
        groups = {}
        
        for anomaly in anomalies:
            # Create grouping key
            if anomaly.anomaly_type in ['zscore_outlier', 'iqr_outlier']:
                # Group by resource for statistical outliers
                group_key = f"resource_{anomaly.resource_id}"
            elif anomaly.anomaly_type == 'percentage_deviation':
                # Group by service for percentage deviations
                group_key = f"service_{anomaly.service}"
            elif anomaly.anomaly_type == 'seasonal_anomaly':
                # Group by service and type for seasonal anomalies
                group_key = f"seasonal_{anomaly.service}"
            else:
                # Default grouping by service
                group_key = f"service_{anomaly.service}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(anomaly)
        
        return groups
    
    def _create_anomaly_alert(self, group_key: str, anomalies: List[AnomalyResult]) -> Optional[Alert]:
        """Create an anomaly alert from grouped anomalies."""
        if not anomalies:
            return None
        
        # Determine alert severity based on highest severity in group
        severity_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        highest_severity = max(anomalies, key=lambda a: severity_map.get(a.severity, 0))
        
        # Create alert title and description
        title, description = self._create_anomaly_alert_content(group_key, anomalies)
        
        # Generate alert ID
        alert_id = self.generate_alert_id()
        
        # Create metadata
        metadata = self._create_anomaly_metadata(anomalies)
        
        # Generate recommendations
        recommendations = self._generate_anomaly_recommendations(anomalies)
        metadata['recommendations'] = recommendations
        
        # Create alert
        alert = Alert(
            id=alert_id,
            title=title,
            description=description,
            severity=self._map_severity(highest_severity.severity),
            status=AlertStatus.ACTIVE,
            source="AnomalyAlertManager",
            timestamp=datetime.now(),
            metadata=metadata,
            tags=['anomaly', 'cost', highest_severity.anomaly_type] + [a.service for a in anomalies]
        )
        
        # Store alert
        self.alerts[alert_id] = alert
        
        return alert
    
    def _create_anomaly_alert_content(self, group_key: str, anomalies: List[AnomalyResult]) -> tuple[str, str]:
        """Create alert title and description."""
        if len(anomalies) == 1:
            anomaly = anomalies[0]
            
            title = f"Cost Anomaly Detected: {anomaly.service} - {anomaly.severity.upper()}"
            
            description = f"""
{anomaly.description}

Resource: {anomaly.resource_id}
Service: {anomaly.service}
Expected Cost: ${anomaly.expected_value:.2f}
Actual Cost: ${anomaly.actual_value:.2f}
Deviation: {anomaly.deviation_percentage:.1f}%
Confidence: {anomaly.confidence_score:.2f}
Date: {anomaly.date.strftime('%Y-%m-%d')}
            """.strip()
        
        else:
            # Multiple anomalies in group
            services = list(set(a.service for a in anomalies))
            total_deviation = sum(a.deviation_percentage for a in anomalies)
            avg_confidence = sum(a.confidence_score for a in anomalies) / len(anomalies)
            
            title = f"Multiple Cost Anomalies Detected: {', '.join(services[:3])}"
            
            if len(services) > 3:
                title += f" and {len(services) - 3} more"
            
            description = f"""
Detected {len(anomalies)} cost anomalies across {len(services)} services.

Summary:
- Total deviation: {total_deviation:.1f}%
- Average confidence: {avg_confidence:.2f}
- Highest severity: {max(a.severity for a in anomalies)}
- Affected services: {', '.join(services)}

Top Anomalies:
{self._format_anomaly_list(anomalies[:5])}
            """.strip()
        
        return title, description
    
    def _create_anomaly_metadata(self, anomalies: List[AnomalyResult]) -> Dict[str, Any]:
        """Create metadata for anomaly alert."""
        if len(anomalies) == 1:
            anomaly = anomalies[0]
            return {
                'anomaly_type': anomaly.anomaly_type,
                'resource_id': anomaly.resource_id,
                'service': anomaly.service,
                'expected_cost': anomaly.expected_value,
                'actual_cost': anomaly.actual_value,
                'deviation_percentage': anomaly.deviation_percentage,
                'confidence_score': anomaly.confidence_score,
                'date': anomaly.date.strftime('%Y-%m-%d'),
                'recommendations': anomaly.recommendations
            }
        else:
            # Multiple anomalies
            services = list(set(a.service for a in anomalies))
            resources = list(set(a.resource_id for a in anomalies))
            
            return {
                'anomaly_count': len(anomalies),
                'affected_services': services,
                'affected_resources': resources,
                'total_deviation': sum(a.deviation_percentage for a in anomalies),
                'average_confidence': sum(a.confidence_score for a in anomalies) / len(anomalies),
                'highest_severity': max(a.severity for a in anomalies),
                'anomaly_types': list(set(a.anomaly_type for a in anomalies)),
                'date_range': {
                    'start': min(a.date for a in anomalies).strftime('%Y-%m-%d'),
                    'end': max(a.date for a in anomalies).strftime('%Y-%m-%d')
                }
            }
    
    def _generate_anomaly_recommendations(self, anomalies: List[AnomalyResult]) -> List[str]:
        """Generate recommendations for anomaly alert."""
        recommendations = []
        
        if len(anomalies) == 1:
            # Single anomaly recommendations
            anomaly = anomalies[0]
            recommendations.extend(anomaly.recommendations)
            
            # Add general recommendations based on anomaly type
            if anomaly.anomaly_type == 'zscore_outlier':
                recommendations.extend([
                    "Investigate sudden cost changes for this resource",
                    "Check for resource misconfiguration or unexpected usage",
                    "Review recent changes that may have impacted costs"
                ])
            elif anomaly.anomaly_type == 'percentage_deviation':
                recommendations.extend([
                    "Compare with historical usage patterns",
                    "Verify if this cost increase is expected",
                    "Consider setting up budget alerts for this resource"
                ])
            elif anomaly.anomaly_type == 'seasonal_anomaly':
                recommendations.extend([
                    "Review weekend or off-hours resource usage",
                    "Consider implementing resource scheduling",
                    "Optimize resource utilization patterns"
                ])
        
        else:
            # Multiple anomalies recommendations
            recommendations.extend([
                "Review overall cost management strategy",
                "Investigate common patterns across affected services",
                "Consider implementing broader cost optimization measures",
                "Monitor spending closely across all affected resources"
            ])
            
            # Add specific recommendations based on anomaly types
            anomaly_types = set(a.anomaly_type for a in anomalies)
            
            if 'zscore_outlier' in anomaly_types:
                recommendations.append("Multiple statistical outliers detected - review resource configurations")
            
            if 'percentage_deviation' in anomaly_types:
                recommendations.append("Significant cost deviations across multiple services - investigate root cause")
            
            if 'seasonal_anomaly' in anomaly_types:
                recommendations.append("Unusual temporal patterns detected - review resource scheduling")
        
        return recommendations
    
    def _format_anomaly_list(self, anomalies: List[AnomalyResult]) -> str:
        """Format list of anomalies for description."""
        lines = []
        for i, anomaly in enumerate(anomalies, 1):
            lines.append(f"{i}. {anomaly.service} ({anomaly.resource_id}): +{anomaly.deviation_percentage:.1f}%")
        return '\n'.join(lines)
    
    def _map_severity(self, anomaly_severity: str) -> AlertSeverity:
        """Map anomaly severity to alert severity."""
        mapping = {
            'low': AlertSeverity.LOW,
            'medium': AlertSeverity.MEDIUM,
            'high': AlertSeverity.HIGH,
            'critical': AlertSeverity.CRITICAL
        }
        return mapping.get(anomaly_severity, AlertSeverity.MEDIUM)
    
    def _prepare_anomaly_template_data(self, alert: Alert) -> Dict[str, Any]:
        """Prepare template data for anomaly alerts."""
        metadata = alert.metadata
        
        if 'anomaly_count' in metadata:
            # Multiple anomalies
            return {
                'anomaly_count': metadata['anomaly_count'],
                'affected_services': ', '.join(metadata['affected_services']),
                'total_deviation': f"{metadata['total_deviation']:.1f}%",
                'average_confidence': f"{metadata['average_confidence']:.2f}",
                'highest_severity': metadata['highest_severity'],
                'anomaly_types': ', '.join(metadata['anomaly_types']),
                'date_range': f"{metadata['date_range']['start']} to {metadata['date_range']['end']}",
                'recommendations': metadata['recommendations']
            }
        else:
            # Single anomaly
            return {
                'anomaly_type': metadata['anomaly_type'],
                'resource_id': metadata['resource_id'],
                'service': metadata['service'],
                'expected_cost': f"${metadata['expected_cost']:.2f}",
                'actual_cost': f"${metadata['actual_cost']:.2f}",
                'deviation_percentage': f"{metadata['deviation_percentage']:.1f}%",
                'confidence_score': f"{metadata['confidence_score']:.2f}",
                'date': metadata['date'],
                'recommendations': metadata['recommendations']
            }
    
    def _is_anomaly_suppressed(self, anomaly: AnomalyResult) -> bool:
        """Check if anomaly is suppressed."""
        # Check resource-level suppression
        resource_key = f"resource_{anomaly.resource_id}"
        if resource_key in self.suppression_rules:
            suppression = self.suppression_rules[resource_key]
            if datetime.now() < suppression['expires_at']:
                return True
            else:
                del self.suppression_rules[resource_key]
        
        # Check service-level suppression
        service_key = f"service_{anomaly.service}"
        if service_key in self.suppression_rules:
            suppression = self.suppression_rules[service_key]
            if datetime.now() < suppression['expires_at']:
                return True
            else:
                del self.suppression_rules[service_key]
        
        return False
    
    def _is_recent_anomaly(self, anomaly: AnomalyResult) -> bool:
        """Check if similar anomaly was recently sent."""
        # Look for similar anomalies in the last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for alert in self.alert_history:
            if alert.timestamp < cutoff_time:
                continue
            
            # Check if alert metadata matches
            metadata = alert.metadata
            
            if (metadata.get('resource_id') == anomaly.resource_id and
                metadata.get('anomaly_type') == anomaly.anomaly_type and
                metadata.get('service') == anomaly.service):
                return True
        
        return False
    
    def _store_anomaly_history(self, anomalies: List[AnomalyResult]) -> None:
        """Store anomalies in history."""
        for anomaly in anomalies:
            history_record = {
                'timestamp': datetime.now().isoformat(),
                'anomaly_type': anomaly.anomaly_type,
                'resource_id': anomaly.resource_id,
                'service': anomaly.service,
                'expected_value': anomaly.expected_value,
                'actual_value': anomaly.actual_value,
                'deviation_percentage': anomaly.deviation_percentage,
                'severity': anomaly.severity,
                'confidence_score': anomaly.confidence_score,
                'date': anomaly.date.isoformat()
            }
            
            self.anomaly_history.append(history_record)
        
        # Keep only last 90 days of history
        cutoff_date = datetime.now() - timedelta(days=90)
        self.anomaly_history = [
            record for record in self.anomaly_history
            if datetime.fromisoformat(record['timestamp']) > cutoff_date
        ]
    
    def _initialize_default_rules(self) -> None:
        """Initialize default anomaly alert rules."""
        default_rules = [
            AlertRule(
                id='anomaly_critical',
                name='Critical Cost Anomaly',
                description='Alert for critical cost anomalies',
                enabled=True,
                severity=AlertSeverity.CRITICAL,
                conditions={'min_severity': 'critical'},
                actions=[{'type': 'notify', 'channels': ['email', 'slack', 'webhook']}],
                cooldown_period=15,  # 15 minutes
                tags=['anomaly', 'critical']
            ),
            AlertRule(
                id='anomaly_high',
                name='High Cost Anomaly',
                description='Alert for high severity cost anomalies',
                enabled=True,
                severity=AlertSeverity.HIGH,
                conditions={'min_severity': 'high'},
                actions=[{'type': 'notify', 'channels': ['email', 'slack']}],
                cooldown_period=30,  # 30 minutes
                tags=['anomaly', 'high']
            ),
            AlertRule(
                id='anomaly_medium',
                name='Medium Cost Anomaly',
                description='Alert for medium severity cost anomalies',
                enabled=True,
                severity=AlertSeverity.MEDIUM,
                conditions={'min_severity': 'medium'},
                actions=[{'type': 'notify', 'channels': ['email']}],
                cooldown_period=60,  # 1 hour
                tags=['anomaly', 'medium']
            ),
            AlertRule(
                id='anomaly_multiple',
                name='Multiple Cost Anomalies',
                description='Alert when multiple anomalies are detected',
                enabled=True,
                severity=AlertSeverity.HIGH,
                conditions={'min_count': 3},
                actions=[{'type': 'notify', 'channels': ['email', 'slack']}],
                cooldown_period=45,  # 45 minutes
                tags=['anomaly', 'multiple']
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def _create_template_manager(self):
        """Create template manager for anomaly alerts."""
        from .templates import AlertTemplateManager
        
        config = {
            'templates_dir': 'templates',
            'default_severity': 'medium'
        }
        return AlertTemplateManager(config)
    
    def get_anomaly_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get anomaly history."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return [
            record for record in self.anomaly_history
            if datetime.fromisoformat(record['timestamp']) > cutoff_date
        ]
    
    def get_anomaly_statistics(self) -> Dict[str, Any]:
        """Get anomaly alert statistics."""
        base_stats = self.get_alert_statistics()
        
        # Add anomaly-specific statistics
        anomaly_alerts = [
            alert for alert in list(self.alerts.values()) + self.alert_history
            if 'anomaly' in alert.tags
        ]
        
        anomaly_types = {}
        for alert in anomaly_alerts:
            anomaly_type = alert.metadata.get('anomaly_type', 'unknown')
            anomaly_types[anomaly_type] = anomaly_types.get(anomaly_type, 0) + 1
        
        affected_services = {}
        for alert in anomaly_alerts:
            services = alert.metadata.get('affected_services', [alert.metadata.get('service', 'unknown')])
            for service in services:
                affected_services[service] = affected_services.get(service, 0) + 1
        
        base_stats.update({
            'anomaly_alerts_total': len(anomaly_alerts),
            'anomaly_alerts_by_type': anomaly_types,
            'affected_services': affected_services,
            'anomaly_history_entries': len(self.anomaly_history),
            'suppressed_anomalies': len(self.suppression_rules)
        })
        
        return base_stats
    
    def suppress_anomaly(self, resource_id: Optional[str] = None, 
                        service: Optional[str] = None,
                        duration_hours: int = 24,
                        reason: str = "Manual suppression") -> bool:
        """Suppress anomalies for a resource or service."""
        try:
            expires_at = datetime.now() + timedelta(hours=duration_hours)
            
            if resource_id:
                key = f"resource_{resource_id}"
                self.suppression_rules[key] = {
                    'type': 'resource',
                    'resource_id': resource_id,
                    'suppressed_at': datetime.now(),
                    'expires_at': expires_at,
                    'reason': reason
                }
            
            if service:
                key = f"service_{service}"
                self.suppression_rules[key] = {
                    'type': 'service',
                    'service': service,
                    'suppressed_at': datetime.now(),
                    'expires_at': expires_at,
                    'reason': reason
                }
            
            return True
            
        except Exception as e:
            raise AlertError(f"Failed to suppress anomaly: {e}")
    
    def check_suppression_expiry(self) -> None:
        """Check and expire anomaly suppression rules."""
        now = datetime.now()
        expired_keys = []
        
        for key, suppression in self.suppression_rules.items():
            if now >= suppression['expires_at']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.suppression_rules[key]
