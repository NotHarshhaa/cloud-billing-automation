"""
Budget alert management system.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from ..core.exceptions import AlertError, BudgetExceededError
from ..analyzers.cost import CostSummary
from .base import BaseAlertManager, Alert, AlertRule, AlertSeverity, AlertStatus
from .channels import ChannelManager


@dataclass
class BudgetStatus:
    """Budget status information."""
    budget_limit: float
    current_spend: float
    forecasted_spend: Optional[float]
    usage_percentage: float
    remaining_budget: float
    days_remaining: int
    daily_average_spend: float
    projected_daily_spend: float
    status: str  # "healthy", "warning", "critical", "exceeded"
    risk_level: str  # "low", "medium", "high", "critical"


@dataclass
class BudgetAlert:
    """Budget-specific alert data."""
    budget_id: str
    budget_name: str
    budget_limit: float
    current_spend: float
    forecasted_spend: Optional[float]
    usage_percentage: float
    alert_type: str  # "threshold", "forecast", "trend"
    severity: AlertSeverity
    recommendations: List[str]


class BudgetAlertManager(BaseAlertManager):
    """Manages budget-related alerts."""
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.budget_config = config.budget
        self.channel_manager = ChannelManager(config.get('notifications', {}))
        self.template_manager = self._create_template_manager()
        self.budget_history: List[Dict[str, Any]] = []
        
        # Initialize default budget rules
        self._initialize_default_rules()
    
    def evaluate_conditions(self, cost_summary: CostSummary) -> List[Alert]:
        """Evaluate budget conditions and generate alerts."""
        alerts = []
        
        try:
            # Calculate budget status
            budget_status = self._calculate_budget_status(cost_summary)
            
            # Store budget status in history
            self._store_budget_status(budget_status)
            
            # Check threshold alerts
            threshold_alerts = self._check_threshold_alerts(budget_status)
            alerts.extend(threshold_alerts)
            
            # Check forecast alerts
            forecast_alerts = self._check_forecast_alerts(budget_status, cost_summary)
            alerts.extend(forecast_alerts)
            
            # Check trend alerts
            trend_alerts = self._check_trend_alerts(budget_status, cost_summary)
            alerts.extend(trend_alerts)
            
            # Send alerts through channels
            for alert in alerts:
                self.send_alert(alert)
            
            return alerts
            
        except Exception as e:
            raise AlertError(f"Failed to evaluate budget conditions: {e}")
    
    def send_alert(self, alert: Alert) -> bool:
        """Send budget alert through configured channels."""
        try:
            # Prepare template data
            template_data = self._prepare_budget_template_data(alert)
            
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
            raise AlertError(f"Failed to send budget alert: {e}")
    
    def get_budget_status(self, cost_summary: CostSummary) -> BudgetStatus:
        """Get current budget status."""
        return self._calculate_budget_status(cost_summary)
    
    def set_budget_limit(self, limit: float) -> None:
        """Update budget limit."""
        self.budget_config.monthly_limit = limit
    
    def get_budget_forecast(self, cost_summary: CostSummary, 
                           days_ahead: int = 30) -> Dict[str, Any]:
        """Generate budget forecast."""
        try:
            current_spend = cost_summary.total_cost
            days_elapsed = (datetime.now().replace(tzinfo=None) - cost_summary.period_start.replace(tzinfo=None)).days
            
            if days_elapsed == 0:
                days_elapsed = 1
            
            daily_average = current_spend / days_elapsed
            
            # Simple linear forecast
            forecasted_spend = daily_average * 30  # 30-day month
            
            # Calculate daily spend trend
            daily_costs = cost_summary.daily_costs
            if len(daily_costs) >= 7:
                recent_days = sorted(daily_costs.keys())[-7:]
                recent_costs = [daily_costs[day] for day in recent_days]
                trend = (recent_costs[-1] - recent_costs[0]) / len(recent_costs)
            else:
                trend = 0
            
            projected_daily = daily_average + trend
            
            return {
                'current_spend': current_spend,
                'forecasted_spend': forecasted_spend,
                'daily_average': daily_average,
                'projected_daily': projected_daily,
                'trend': 'increasing' if trend > 0 else 'decreasing' if trend < 0 else 'stable',
                'confidence': 'medium' if len(daily_costs) >= 14 else 'low'
            }
            
        except Exception as e:
            raise AlertError(f"Failed to generate budget forecast: {e}")
    
    def _calculate_budget_status(self, cost_summary: CostSummary) -> BudgetStatus:
        """Calculate current budget status."""
        budget_limit = self.budget_config.monthly_limit
        current_spend = cost_summary.total_cost
        usage_percentage = (current_spend / budget_limit * 100) if budget_limit > 0 else 0
        remaining_budget = budget_limit - current_spend
        
        # Calculate days remaining in month
        now = datetime.now()
        end_of_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        days_remaining = (end_of_month - now).days
        
        # Calculate daily averages
        days_elapsed = (now.replace(tzinfo=None) - cost_summary.period_start.replace(tzinfo=None)).days
        if days_elapsed == 0:
            days_elapsed = 1
        
        daily_average_spend = current_spend / days_elapsed
        projected_daily_spend = remaining_budget / days_remaining if days_remaining > 0 else 0
        
        # Determine status and risk level
        if usage_percentage >= 100:
            status = "exceeded"
            risk_level = "critical"
        elif usage_percentage >= self.budget_config.critical_threshold * 100:
            status = "critical"
            risk_level = "critical"
        elif usage_percentage >= self.budget_config.warning_threshold * 100:
            status = "warning"
            risk_level = "high"
        elif usage_percentage >= 50:
            status = "healthy"
            risk_level = "medium"
        else:
            status = "healthy"
            risk_level = "low"
        
        # Get forecasted spend
        forecast = self.get_budget_forecast(cost_summary)
        forecasted_spend = forecast.get('forecasted_spend')
        
        return BudgetStatus(
            budget_limit=budget_limit,
            current_spend=current_spend,
            forecasted_spend=forecasted_spend,
            usage_percentage=usage_percentage,
            remaining_budget=remaining_budget,
            days_remaining=days_remaining,
            daily_average_spend=daily_average_spend,
            projected_daily_spend=projected_daily_spend,
            status=status,
            risk_level=risk_level
        )
    
    def _check_threshold_alerts(self, budget_status: BudgetStatus) -> List[Alert]:
        """Check budget threshold alerts."""
        alerts = []
        
        # Warning threshold
        if budget_status.usage_percentage >= self.budget_config.warning_threshold * 100:
            warning_rule = self.rules.get('budget_warning')
            if warning_rule and not self.is_in_cooldown('budget_warning'):
                alert = self._create_budget_alert(
                    budget_status,
                    'threshold',
                    AlertSeverity.MEDIUM,
                    f"Budget Warning: {budget_status.usage_percentage:.1f}% used"
                )
                alerts.append(alert)
        
        # Critical threshold
        if budget_status.usage_percentage >= self.budget_config.critical_threshold * 100:
            critical_rule = self.rules.get('budget_critical')
            if critical_rule and not self.is_in_cooldown('budget_critical'):
                alert = self._create_budget_alert(
                    budget_status,
                    'threshold',
                    AlertSeverity.HIGH,
                    f"Budget Critical: {budget_status.usage_percentage:.1f}% used"
                )
                alerts.append(alert)
        
        # Budget exceeded
        if budget_status.usage_percentage >= 100:
            exceeded_rule = self.rules.get('budget_exceeded')
            if exceeded_rule and not self.is_in_cooldown('budget_exceeded'):
                alert = self._create_budget_alert(
                    budget_status,
                    'threshold',
                    AlertSeverity.CRITICAL,
                    f"Budget Exceeded: {budget_status.usage_percentage:.1f}% used"
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_forecast_alerts(self, budget_status: BudgetStatus, 
                              cost_summary: CostSummary) -> List[Alert]:
        """Check forecast-based alerts."""
        alerts = []
        
        if not budget_status.forecasted_spend:
            return alerts
        
        forecast_percentage = (budget_status.forecasted_spend / budget_status.budget_limit * 100)
        
        # Forecast warning
        if forecast_percentage >= 90:
            forecast_rule = self.rules.get('budget_forecast_warning')
            if forecast_rule and not self.is_in_cooldown('budget_forecast_warning'):
                alert = self._create_budget_alert(
                    budget_status,
                    'forecast',
                    AlertSeverity.MEDIUM,
                    f"Budget Forecast Warning: Projected {forecast_percentage:.1f}% usage"
                )
                alerts.append(alert)
        
        # Forecast critical
        if forecast_percentage >= 100:
            forecast_rule = self.rules.get('budget_forecast_critical')
            if forecast_rule and not self.is_in_cooldown('budget_forecast_critical'):
                alert = self._create_budget_alert(
                    budget_status,
                    'forecast',
                    AlertSeverity.HIGH,
                    f"Budget Forecast Critical: Projected {forecast_percentage:.1f}% usage"
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_trend_alerts(self, budget_status: BudgetStatus, 
                           cost_summary: CostSummary) -> List[Alert]:
        """Check trend-based alerts."""
        alerts = []
        
        # Check if daily spend is increasing rapidly
        if len(cost_summary.daily_costs) >= 7:
            daily_costs = sorted(cost_summary.daily_costs.items())
            recent_costs = [cost for date, cost in daily_costs[-7:]]
            
            if len(recent_costs) >= 3:
                # Calculate trend
                first_half_avg = sum(recent_costs[:len(recent_costs)//2]) / (len(recent_costs)//2)
                second_half_avg = sum(recent_costs[len(recent_costs)//2:]) / (len(recent_costs) - len(recent_costs)//2)
                
                if first_half_avg > 0:
                    trend_increase = (second_half_avg - first_half_avg) / first_half_avg * 100
                    
                    # Alert if trend is increasing by more than 50%
                    if trend_increase >= 50:
                        trend_rule = self.rules.get('budget_trend_increase')
                        if trend_rule and not self.is_in_cooldown('budget_trend_increase'):
                            alert = self._create_budget_alert(
                                budget_status,
                                'trend',
                                AlertSeverity.MEDIUM,
                                f"Budget Trend Alert: Daily spending increased by {trend_increase:.1f}%"
                            )
                            alerts.append(alert)
        
        return alerts
    
    def _create_budget_alert(self, budget_status: BudgetStatus, alert_type: str,
                           severity: AlertSeverity, title: str) -> Alert:
        """Create a budget alert."""
        alert_id = self.generate_alert_id()
        
        # Generate recommendations
        recommendations = self._generate_budget_recommendations(budget_status, alert_type)
        
        # Create description
        description = self._create_budget_description(budget_status, alert_type)
        
        alert = Alert(
            id=alert_id,
            title=title,
            description=description,
            severity=severity,
            status=AlertStatus.ACTIVE,
            source="BudgetAlertManager",
            timestamp=datetime.now(),
            metadata={
                'budget_id': 'main',
                'budget_name': 'Monthly Budget',
                'budget_limit': budget_status.budget_limit,
                'current_spend': budget_status.current_spend,
                'forecasted_spend': budget_status.forecasted_spend,
                'usage_percentage': budget_status.usage_percentage,
                'remaining_budget': budget_status.remaining_budget,
                'days_remaining': budget_status.days_remaining,
                'daily_average_spend': budget_status.daily_average_spend,
                'projected_daily_spend': budget_status.projected_daily_spend,
                'status': budget_status.status,
                'risk_level': budget_status.risk_level,
                'alert_type': alert_type,
                'recommendations': recommendations
            },
            tags=['budget', 'cost', alert_type]
        )
        
        # Store alert
        self.alerts[alert_id] = alert
        
        return alert
    
    def _create_budget_description(self, budget_status: BudgetStatus, alert_type: str) -> str:
        """Create budget alert description."""
        if alert_type == 'threshold':
            return f"""
Current budget usage is {budget_status.usage_percentage:.1f}% (${budget_status.current_spend:.2f}) of the monthly budget limit (${budget_status.budget_limit:.2f}).

Remaining budget: ${budget_status.remaining_budget:.2f}
Days remaining: {budget_status.days_remaining}
Daily average spend: ${budget_status.daily_average_spend:.2f}
            """.strip()
        
        elif alert_type == 'forecast':
            return f"""
Based on current spending patterns, the forecasted monthly spend is ${budget_status.forecasted_spend:.2f}, which is {(budget_status.forecasted_spend / budget_status.budget_limit * 100):.1f}% of the budget limit.

Current spend: ${budget_status.current_spend:.2f} ({budget_status.usage_percentage:.1f}%)
Budget limit: ${budget_status.budget_limit:.2f}
            """.strip()
        
        elif alert_type == 'trend':
            return f"""
Daily spending has shown a significant increasing trend over the past week. This may lead to budget overruns if the trend continues.

Current daily average: ${budget_status.daily_average_spend:.2f}
Projected daily spend: ${budget_status.projected_daily_spend:.2f}
            """.strip()
        
        else:
            return f"Budget alert: {budget_status.status} - {budget_status.usage_percentage:.1f}% used"
    
    def _generate_budget_recommendations(self, budget_status: BudgetStatus, alert_type: str) -> List[str]:
        """Generate budget recommendations."""
        recommendations = []
        
        if budget_status.usage_percentage >= 100:
            recommendations.extend([
                "Immediate action required - budget has been exceeded",
                "Review all recent spending and identify non-essential costs",
                "Consider implementing cost optimization measures immediately",
                "Freeze non-critical resource provisioning"
            ])
        
        elif budget_status.usage_percentage >= self.budget_config.critical_threshold * 100:
            recommendations.extend([
                "Review current spending patterns and identify optimization opportunities",
                "Consider scaling down non-production resources",
                "Implement stricter spending controls",
                "Monitor usage closely until end of billing period"
            ])
        
        elif budget_status.usage_percentage >= self.budget_config.warning_threshold * 100:
            recommendations.extend([
                "Review resource utilization and rightsizing opportunities",
                "Consider implementing resource scheduling for non-production workloads",
                "Monitor spending trends closely",
                "Plan for potential cost optimization measures"
            ])
        
        if alert_type == 'forecast' and budget_status.forecasted_spend:
            if budget_status.forecasted_spend > budget_status.budget_limit:
                recommendations.append("Forecast indicates budget will be exceeded - take preventive action")
            else:
                recommendations.append("Monitor spending to ensure forecast remains accurate")
        
        if alert_type == 'trend':
            recommendations.extend([
                "Investigate cause of increasing daily spending",
                "Check for resource misconfiguration or unexpected usage",
                "Review recent changes that may have impacted costs"
            ])
        
        return recommendations
    
    def _prepare_budget_template_data(self, alert: Alert) -> Dict[str, Any]:
        """Prepare template data for budget alerts."""
        return {
            'budget_status': alert.metadata.get('status', 'unknown'),
            'current_spend': f"${alert.metadata.get('current_spend', 0):.2f}",
            'budget_limit': f"${alert.metadata.get('budget_limit', 0):.2f}",
            'usage_percentage': f"{alert.metadata.get('usage_percentage', 0):.1f}%",
            'forecasted_spend': f"${alert.metadata.get('forecasted_spend', 0):.2f}" if alert.metadata.get('forecasted_spend') else "N/A",
            'remaining_budget': f"${alert.metadata.get('remaining_budget', 0):.2f}",
            'days_remaining': alert.metadata.get('days_remaining', 0),
            'daily_average': f"${alert.metadata.get('daily_average_spend', 0):.2f}",
            'risk_level': alert.metadata.get('risk_level', 'unknown'),
            'recommendations': alert.metadata.get('recommendations', [])
        }
    
    def _store_budget_status(self, budget_status: BudgetStatus) -> None:
        """Store budget status in history."""
        status_record = {
            'timestamp': datetime.now().isoformat(),
            'budget_limit': budget_status.budget_limit,
            'current_spend': budget_status.current_spend,
            'usage_percentage': budget_status.usage_percentage,
            'status': budget_status.status,
            'risk_level': budget_status.risk_level
        }
        
        self.budget_history.append(status_record)
        
        # Keep only last 90 days of history
        cutoff_date = datetime.now() - timedelta(days=90)
        self.budget_history = [
            record for record in self.budget_history
            if datetime.fromisoformat(record['timestamp']) > cutoff_date
        ]
    
    def _initialize_default_rules(self) -> None:
        """Initialize default budget alert rules."""
        default_rules = [
            AlertRule(
                id='budget_warning',
                name='Budget Warning Threshold',
                description='Alert when budget usage reaches warning threshold',
                enabled=True,
                severity=AlertSeverity.MEDIUM,
                conditions={'threshold': self.budget_config.warning_threshold},
                actions=[{'type': 'notify', 'channels': ['email', 'slack']}],
                cooldown_period=60,  # 1 hour
                tags=['budget', 'threshold', 'warning']
            ),
            AlertRule(
                id='budget_critical',
                name='Budget Critical Threshold',
                description='Alert when budget usage reaches critical threshold',
                enabled=True,
                severity=AlertSeverity.HIGH,
                conditions={'threshold': self.budget_config.critical_threshold},
                actions=[{'type': 'notify', 'channels': ['email', 'slack', 'webhook']}],
                cooldown_period=30,  # 30 minutes
                tags=['budget', 'threshold', 'critical']
            ),
            AlertRule(
                id='budget_exceeded',
                name='Budget Exceeded',
                description='Alert when budget is exceeded',
                enabled=True,
                severity=AlertSeverity.CRITICAL,
                conditions={'threshold': 1.0},
                actions=[{'type': 'notify', 'channels': ['email', 'slack', 'webhook']}],
                cooldown_period=15,  # 15 minutes
                tags=['budget', 'threshold', 'exceeded']
            ),
            AlertRule(
                id='budget_forecast_warning',
                name='Budget Forecast Warning',
                description='Alert when forecast indicates budget risk',
                enabled=True,
                severity=AlertSeverity.MEDIUM,
                conditions={'forecast_threshold': 0.9},
                actions=[{'type': 'notify', 'channels': ['email']}],
                cooldown_period=120,  # 2 hours
                tags=['budget', 'forecast', 'warning']
            ),
            AlertRule(
                id='budget_trend_increase',
                name='Budget Trend Increase',
                description='Alert when daily spending trend increases significantly',
                enabled=True,
                severity=AlertSeverity.MEDIUM,
                conditions={'trend_increase': 0.5},
                actions=[{'type': 'notify', 'channels': ['email']}],
                cooldown_period=180,  # 3 hours
                tags=['budget', 'trend', 'increase']
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def _create_template_manager(self):
        """Create template manager for budget alerts."""
        from .templates import AlertTemplateManager
        
        config = {
            'templates_dir': 'templates',
            'default_severity': 'medium'
        }
        return AlertTemplateManager(config)
    
    def get_budget_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get budget status history."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return [
            record for record in self.budget_history
            if datetime.fromisoformat(record['timestamp']) > cutoff_date
        ]
    
    def get_budget_statistics(self) -> Dict[str, Any]:
        """Get budget alert statistics."""
        base_stats = self.get_alert_statistics()
        
        # Add budget-specific statistics
        budget_alerts = [
            alert for alert in list(self.alerts.values()) + self.alert_history
            if 'budget' in alert.tags
        ]
        
        alert_types = {}
        for alert in budget_alerts:
            alert_type = alert.metadata.get('alert_type', 'unknown')
            alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
        
        base_stats.update({
            'budget_alerts_total': len(budget_alerts),
            'budget_alerts_by_type': alert_types,
            'budget_history_entries': len(self.budget_history),
            'current_budget_limit': self.budget_config.monthly_limit,
            'warning_threshold': self.budget_config.warning_threshold,
            'critical_threshold': self.budget_config.critical_threshold
        })
        
        return base_stats
