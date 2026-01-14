"""
Base alert management system.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from ..core.exceptions import AlertError


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Base alert data structure."""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    timestamp: datetime
    metadata: Dict[str, Any]
    tags: List[str]
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value,
            'status': self.status.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'tags': self.tags,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""
    id: str
    name: str
    description: str
    enabled: bool
    severity: AlertSeverity
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    cooldown_period: int  # minutes
    escalation_policy: Optional[str] = None
    tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'severity': self.severity.value,
            'conditions': self.conditions,
            'actions': self.actions,
            'cooldown_period': self.cooldown_period,
            'escalation_policy': self.escalation_policy,
            'tags': self.tags,
        }


class BaseAlertManager(ABC):
    """Base class for alert managers."""
    
    def __init__(self, config: Any):
        self.config = config
        self.alerts: Dict[str, Alert] = {}
        self.rules: Dict[str, AlertRule] = {}
        self.alert_history: List[Alert] = []
        self.suppression_rules: Dict[str, Dict[str, Any]] = {}
    
    @abstractmethod
    def evaluate_conditions(self, data: Any) -> List[Alert]:
        """Evaluate alert conditions and generate alerts."""
        pass
    
    @abstractmethod
    def send_alert(self, alert: Alert) -> bool:
        """Send alert through configured channels."""
        pass
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self.rules[rule.id] = rule
    
    def remove_rule(self, rule_id: str) -> None:
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get an alert rule by ID."""
        return self.rules.get(rule_id)
    
    def list_rules(self) -> List[AlertRule]:
        """List all alert rules."""
        return list(self.rules.values())
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID."""
        return self.alerts.get(alert_id)
    
    def list_alerts(self, status: Optional[AlertStatus] = None, 
                   severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """List alerts with optional filtering."""
        alerts = list(self.alerts.values())
        
        if status:
            alerts = [alert for alert in alerts if alert.status == status]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()
        
        return True
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        
        # Move to history
        self.alert_history.append(alert)
        del self.alerts[alert_id]
        
        return True
    
    def suppress_alert(self, alert_id: str, duration_minutes: int, 
                      reason: str) -> bool:
        """Suppress an alert for a specified duration."""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.status = AlertStatus.SUPPRESSED
        
        # Add suppression rule
        self.suppression_rules[alert_id] = {
            'alert_id': alert_id,
            'suppressed_at': datetime.now(),
            'duration_minutes': duration_minutes,
            'reason': reason,
            'expires_at': datetime.now() + timedelta(minutes=duration_minutes)
        }
        
        return True
    
    def check_suppression_expiry(self) -> None:
        """Check and expire suppression rules."""
        now = datetime.now()
        expired_suppressions = []
        
        for alert_id, suppression in self.suppression_rules.items():
            if now >= suppression['expires_at']:
                expired_suppressions.append(alert_id)
                
                # Reactivate alert if it still exists
                if alert_id in self.alerts:
                    self.alerts[alert_id].status = AlertStatus.ACTIVE
        
        # Remove expired suppression rules
        for alert_id in expired_suppressions:
            del self.suppression_rules[alert_id]
    
    def generate_alert_id(self) -> str:
        """Generate a unique alert ID."""
        import uuid
        return str(uuid.uuid4())
    
    def is_in_cooldown(self, rule_id: str) -> bool:
        """Check if a rule is in cooldown period."""
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        
        # Check if we have recent alerts for this rule
        recent_alerts = [
            alert for alert in self.alert_history
            if alert.metadata.get('rule_id') == rule_id and
            (datetime.now() - alert.timestamp).total_seconds() < rule.cooldown_period * 60
        ]
        
        return len(recent_alerts) > 0
    
    def evaluate_rule(self, rule: AlertRule, data: Any) -> Optional[Alert]:
        """Evaluate a single rule against data."""
        if not rule.enabled:
            return None
        
        if self.is_in_cooldown(rule.id):
            return None
        
        # Check if rule conditions are met
        if self._check_conditions(rule.conditions, data):
            alert_id = self.generate_alert_id()
            
            alert = Alert(
                id=alert_id,
                title=rule.name,
                description=rule.description,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                source=self.__class__.__name__,
                timestamp=datetime.now(),
                metadata={
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'evaluated_at': datetime.now().isoformat(),
                    'data_summary': self._summarize_data(data)
                },
                tags=rule.tags
            )
            
            # Store alert
            self.alerts[alert_id] = alert
            
            return alert
        
        return None
    
    def _check_conditions(self, conditions: Dict[str, Any], data: Any) -> bool:
        """Check if alert conditions are met."""
        # This should be implemented by subclasses
        # For now, return False as default
        return False
    
    def _summarize_data(self, data: Any) -> Dict[str, Any]:
        """Create a summary of the data that triggered the alert."""
        try:
            if hasattr(data, '__dict__'):
                return {
                    'type': type(data).__name__,
                    'attributes': list(data.__dict__.keys())
                }
            elif isinstance(data, dict):
                return {
                    'type': 'dict',
                    'keys': list(data.keys())
                }
            elif isinstance(data, (list, tuple)):
                return {
                    'type': type(data).__name__,
                    'length': len(data)
                }
            else:
                return {
                    'type': type(data).__name__,
                    'value': str(data)[:100]  # Truncate long values
                }
        except Exception:
            return {
                'type': 'unknown',
                'error': 'Failed to summarize data'
            }
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        total_alerts = len(self.alert_history) + len(self.alerts)
        
        status_counts = {}
        for alert in list(self.alerts.values()) + self.alert_history:
            status_counts[alert.status.value] = status_counts.get(alert.status.value, 0) + 1
        
        severity_counts = {}
        for alert in list(self.alerts.values()) + self.alert_history:
            severity_counts[alert.severity.value] = severity_counts.get(alert.severity.value, 0) + 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': len(self.alerts),
            'resolved_alerts': len(self.alert_history),
            'alerts_by_status': status_counts,
            'alerts_by_severity': severity_counts,
            'suppressed_alerts': len(self.suppression_rules),
            'rules_configured': len(self.rules),
            'rules_enabled': len([r for r in self.rules.values() if r.enabled])
        }
