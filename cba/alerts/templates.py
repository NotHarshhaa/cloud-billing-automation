"""
Alert template management system.
"""

from jinja2 import Environment, Template, FileSystemLoader
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from ..core.exceptions import AlertError
from .base import Alert


class AlertTemplateManager:
    """Manages alert templates for different channels and contexts."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.templates_dir = Path(config.get('templates_dir', 'templates'))
        self.default_templates = self._create_default_templates()
        self.custom_templates = {}
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)) if self.templates_dir.exists() else None,
            autoescape=True
        )
        
        # Load custom templates if directory exists
        if self.templates_dir.exists():
            self._load_custom_templates()
    
    def render_template(self, template_name: str, alert: Alert, 
                        additional_data: Optional[Dict[str, Any]] = None) -> str:
        """Render an alert template."""
        try:
            # Get template content
            template_content = self._get_template_content(template_name)
            
            # Create Jinja template
            template = Template(template_content)
            
            # Prepare template data
            template_data = self._prepare_template_data(alert, additional_data)
            
            # Render template
            return template.render(**template_data)
            
        except Exception as e:
            raise AlertError(f"Failed to render template {template_name}: {e}")
    
    def _get_template_content(self, template_name: str) -> str:
        """Get template content by name."""
        # Try custom template first
        if template_name in self.custom_templates:
            return self.custom_templates[template_name]
        
        # Try file-based template
        if self.jinja_env.loader:
            try:
                template = self.jinja_env.get_template(template_name)
                return template.source
            except:
                pass
        
        # Fall back to default template
        if template_name in self.default_templates:
            return self.default_templates[template_name]
        
        # If no template found, use basic template
        return self.default_templates.get('basic', self._create_basic_template())
    
    def _prepare_template_data(self, alert: Alert, 
                              additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare data for template rendering."""
        base_data = {
            'alert': alert,
            'alert_id': alert.id,
            'title': alert.title,
            'description': alert.description,
            'severity': alert.severity.value,
            'status': alert.status.value,
            'source': alert.source,
            'timestamp': alert.timestamp,
            'metadata': alert.metadata,
            'tags': alert.tags,
            'now': datetime.now(),
            'severity_emoji': self._get_severity_emoji(alert.severity.value),
            'severity_color': self._get_severity_color(alert.severity.value),
        }
        
        if additional_data:
            base_data.update(additional_data)
        
        return base_data
    
    def _get_severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level."""
        emoji_map = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }
        return emoji_map.get(severity, '⚪')
    
    def _get_severity_color(self, severity: str) -> str:
        """Get color for severity level."""
        color_map = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545'
        }
        return color_map.get(severity, '#6c757d')
    
    def _create_default_templates(self) -> Dict[str, str]:
        """Create default alert templates."""
        return {
            'email_html': self._create_email_html_template(),
            'email_text': self._create_email_text_template(),
            'slack': self._create_slack_template(),
            'webhook': self._create_webhook_template(),
            'basic': self._create_basic_template(),
            'budget_alert': self._create_budget_alert_template(),
            'anomaly_alert': self._create_anomaly_alert_template(),
            'resource_alert': self._create_resource_alert_template(),
        }
    
    def _create_basic_template(self) -> str:
        """Create basic alert template."""
        return """
Alert: {{ title }}
Severity: {{ severity_emoji }} {{ severity|upper }}
Status: {{ status|upper }}
Source: {{ source }}
Timestamp: {{ timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') }}

Description:
{{ description }}

{% if metadata %}
Additional Information:
{% for key, value in metadata.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

{% if tags %}
Tags: {{ tags|join(', ') }}
{% endif %}
        """.strip()
    
    def _create_email_html_template(self) -> str:
        """Create HTML email template."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Cloud Billing Alert</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background-color: {{ severity_color }}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { padding: 20px; }
        .severity { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; font-weight: bold; }
        .metadata { background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 10px 0; }
        .footer { background-color: #f8f9fa; padding: 15px; border-radius: 0 0 8px 8px; font-size: 12px; color: #6c757d; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background-color: #f8f9fa; }
        .action-button { display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ severity_emoji }} Cloud Billing Alert</h1>
            <span class="severity">{{ severity|upper }}</span>
        </div>
        <div class="content">
            <h2>{{ title }}</h2>
            <p>{{ description }}</p>
            
            <div class="metadata">
                <h3>Alert Details</h3>
                <table>
                    <tr><th>Alert ID</th><td>{{ alert_id }}</td></tr>
                    <tr><th>Source</th><td>{{ source }}</td></tr>
                    <tr><th>Timestamp</th><td>{{ timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') }}</td></tr>
                    <tr><th>Status</th><td>{{ status|upper }}</td></tr>
                </table>
            </div>
            
            {% if metadata %}
            <div class="metadata">
                <h3>Additional Information</h3>
                <table>
                {% for key, value in metadata.items() %}
                    <tr><th>{{ key }}</th><td>{{ value }}</td></tr>
                {% endfor %}
                </table>
            </div>
            {% endif %}
            
            {% if tags %}
            <div class="metadata">
                <h3>Tags</h3>
                <p>{{ tags|join(', ') }}</p>
            </div>
            {% endif %}
            
            <div class="action-button">
                <a href="#" style="color: white; text-decoration: none;">View in Dashboard</a>
            </div>
        </div>
        <div class="footer">
            <p>This alert was generated by Cloud Billing Automation Tool at {{ now.strftime('%Y-%m-%d %H:%M:%S UTC') }}.</p>
            <p>If you believe this is a false positive, please acknowledge the alert in the dashboard.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _create_email_text_template(self) -> str:
        """Create plain text email template."""
        return """
{{ severity_emoji }} CLOUD BILLING ALERT - {{ severity|upper }}

{{ title }}

{{ description }}

ALERT DETAILS:
------------
Alert ID: {{ alert_id }}
Source: {{ source }}
Timestamp: {{ timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') }}
Status: {{ status|upper }}

{% if metadata %}
ADDITIONAL INFORMATION:
----------------------
{% for key, value in metadata.items() %}
{{ key }}: {{ value }}
{% endfor %}
{% endif %}

{% if tags %}
TAGS: {{ tags|join(', ') }}
{% endif %}

---
This alert was generated by Cloud Billing Automation Tool at {{ now.strftime('%Y-%m-%d %H:%M:%S UTC') }}.
        """.strip()
    
    def _create_slack_template(self) -> str:
        """Create Slack message template."""
        return """
{
    "text": "{{ severity_emoji }} {{ title }}",
    "attachments": [
        {
            "color": "{{ severity_color }}",
            "title": "{{ title }}",
            "text": "{{ description }}",
            "fields": [
                {
                    "title": "Severity",
                    "value": "{{ severity|upper }}",
                    "short": true
                },
                {
                    "title": "Status",
                    "value": "{{ status|upper }}",
                    "short": true
                },
                {
                    "title": "Source",
                    "value": "{{ source }}",
                    "short": true
                },
                {
                    "title": "Timestamp",
                    "value": "{{ timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') }}",
                    "short": true
                }{% if metadata %},
                {% for key, value in metadata.items() %}
                {
                    "title": "{{ key }}",
                    "value": "{{ value }}",
                    "short": true
                }{% if not loop.last %},{% endif %}
                {% endfor %}{% endif %}
            ],
            "footer": "Cloud Billing Automation",
            "ts": {{ timestamp.timestamp() }}
        }
    ]
}
        """.strip()
    
    def _create_webhook_template(self) -> str:
        """Create webhook JSON template."""
        return """
{
    "alert": {
        "id": "{{ alert_id }}",
        "title": "{{ title }}",
        "description": "{{ description }}",
        "severity": "{{ severity }}",
        "status": "{{ status }}",
        "source": "{{ source }}",
        "timestamp": "{{ timestamp.isoformat() }}",
        "metadata": {{ metadata | tojson }},
        "tags": {{ tags | tojson }}
    },
    "notification": {
        "severity_emoji": "{{ severity_emoji }}",
        "severity_color": "{{ severity_color }}",
        "generated_at": "{{ now.isoformat() }}"
    }
}
        """.strip()
    
    def _create_budget_alert_template(self) -> str:
        """Create budget-specific alert template."""
        return """
🚨 BUDGET ALERT - {{ severity|upper }}

Budget Status: {{ metadata.budget_status }}
Current Spend: ${{ metadata.current_spend }}
Budget Limit: ${{ metadata.budget_limit }}
Usage Percentage: {{ metadata.usage_percentage }}%

{% if metadata.forecasted_spend %}
Forecasted Spend: ${{ metadata.forecasted_spend }}
{% endif %}

{{ description }}

RECOMMENDATIONS:
{% if metadata.recommendations %}
{% for recommendation in metadata.recommendations %}
- {{ recommendation }}
{% endfor %}
{% else %}
- Review current spending patterns
- Consider implementing cost optimization measures
- Monitor usage closely until end of billing period
{% endif %}

ALERT DETAILS:
------------
Alert ID: {{ alert_id }}
Source: {{ source }}
Timestamp: {{ timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') }}

---
Generated by Cloud Billing Automation Tool
        """.strip()
    
    def _create_anomaly_alert_template(self) -> str:
        """Create anomaly-specific alert template."""
        return """
🔍 ANOMALY DETECTED - {{ severity|upper }}

{{ title }}

{{ description }}

ANOMALY DETAILS:
---------------
Expected Cost: ${{ metadata.expected_cost }}
Actual Cost: ${{ metadata.actual_cost }}
Deviation: {{ metadata.deviation_percentage }}%
Confidence: {{ metadata.confidence_score }}%

Resource: {{ metadata.resource_id }}
Service: {{ metadata.service }}
Date: {{ metadata.date }}

ANALYSIS:
--------
{% if metadata.anomaly_type == 'zscore_outlier' %}
Detected using Z-score analysis. Cost spike is {{ metadata.deviation_percentage }}% above historical average.
{% elif metadata.anomaly_type == 'iqr_outlier' %}
Detected using Interquartile Range method. Cost is outside normal range.
{% elif metadata.anomaly_type == 'percentage_deviation' %}
Detected {{ metadata.deviation_percentage }}% deviation from historical average.
{% endif %}

RECOMMENDATIONS:
{% if metadata.recommendations %}
{% for recommendation in metadata.recommendations %}
- {{ recommendation }}
{% endfor %}
{% else %}
- Investigate the cause of cost increase
- Check for resource misconfiguration
- Verify if this cost is legitimate
- Consider setting up budget alerts
{% endif %}

ALERT DETAILS:
------------
Alert ID: {{ alert_id }}
Source: {{ source }}
Timestamp: {{ timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') }}

---
Generated by Cloud Billing Automation Tool
        """.strip()
    
    def _create_resource_alert_template(self) -> str:
        """Create resource-specific alert template."""
        return """
🖥️ RESOURCE ALERT - {{ severity|upper }}

{{ title }}

{{ description }}

RESOURCE DETAILS:
-----------------
Resource ID: {{ metadata.resource_id }}
Resource Name: {{ metadata.resource_name }}
Resource Type: {{ metadata.resource_type }}
Region: {{ metadata.region }}
Environment: {{ metadata.environment }}

COST INFORMATION:
-----------------
Total Cost: ${{ metadata.total_cost }}
Daily Average: ${{ metadata.daily_average_cost }}
Cost Trend: {{ metadata.cost_trend }}
Efficiency Score: {{ metadata.efficiency_score }}

OPTIMIZATION RECOMMENDATIONS:
{% if metadata.recommendations %}
{% for recommendation in metadata.recommendations %}
- {{ recommendation }}
{% endfor %}
{% else %}
- Review resource utilization
- Consider rightsizing if underutilized
- Implement scheduling for non-production workloads
- Review storage lifecycle policies
{% endif %}

ALERT DETAILS:
------------
Alert ID: {{ alert_id }}
Source: {{ source }}
Timestamp: {{ timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') }}

---
Generated by Cloud Billing Automation Tool
        """.strip()
    
    def _load_custom_templates(self) -> None:
        """Load custom templates from files."""
        try:
            for template_file in self.templates_dir.glob("*.j2"):
                template_name = template_file.stem
                with open(template_file, 'r', encoding='utf-8') as f:
                    self.custom_templates[template_name] = f.read()
        except Exception as e:
            print(f"Warning: Failed to load custom templates: {e}")
    
    def add_custom_template(self, name: str, content: str) -> None:
        """Add a custom template."""
        self.custom_templates[name] = content
    
    def remove_custom_template(self, name: str) -> None:
        """Remove a custom template."""
        if name in self.custom_templates:
            del self.custom_templates[name]
    
    def list_templates(self) -> List[str]:
        """List all available templates."""
        templates = list(self.default_templates.keys())
        templates.extend(self.custom_templates.keys())
        return sorted(list(set(templates)))
    
    def save_custom_template(self, name: str, content: str) -> None:
        """Save custom template to file."""
        try:
            self.templates_dir.mkdir(exist_ok=True)
            template_file = self.templates_dir / f"{name}.j2"
            
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.custom_templates[name] = content
            
        except Exception as e:
            raise AlertError(f"Failed to save custom template {name}: {e}")
    
    def validate_template(self, template_content: str) -> Dict[str, Any]:
        """Validate template syntax."""
        try:
            template = Template(template_content)
            
            # Try to render with sample data
            sample_alert = Alert(
                id="test-id",
                title="Test Alert",
                description="Test description",
                severity=self.config.get('default_severity', 'medium'),
                status="active",
                source="test",
                timestamp=datetime.now(),
                metadata={},
                tags=[]
            )
            
            template.render(alert=sample_alert)
            
            return {
                'valid': True,
                'errors': []
            }
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [str(e)]
            }
