"""
Alert notification channels (email, webhook, Slack).
"""

import smtplib
import requests
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from ..core.exceptions import AlertError
from .base import Alert


class BaseChannel(ABC):
    """Base class for alert notification channels."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
        self.name = config.get('name', self.__class__.__name__)
    
    @abstractmethod
    def send(self, alert: Alert, template_data: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert through this channel."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to the channel."""
        pass
    
    def is_enabled(self) -> bool:
        """Check if channel is enabled."""
        return self.enabled


class EmailChannel(BaseChannel):
    """Email notification channel."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email')
        self.to_emails = config.get('to_emails', [])
        self.use_tls = config.get('use_tls', True)
    
    def send(self, alert: Alert, template_data: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert via email."""
        try:
            if not self.is_enabled():
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Create HTML body
            html_body = self._create_html_body(alert, template_data)
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            raise AlertError(f"Failed to send email alert: {e}")
    
    def test_connection(self) -> bool:
        """Test SMTP connection."""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
            return True
        except Exception:
            return False
    
    def _create_html_body(self, alert: Alert, template_data: Optional[Dict[str, Any]] = None) -> str:
        """Create HTML email body."""
        severity_colors = {
            'low': '#28a745',
            'medium': '#ffc107', 
            'high': '#fd7e14',
            'critical': '#dc3545'
        }
        
        color = severity_colors.get(alert.severity.value, '#6c757d')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Cloud Billing Alert</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ padding: 20px; }}
                .severity {{ display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; font-weight: bold; }}
                .metadata {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 10px 0; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; border-radius: 0 0 8px 8px; font-size: 12px; color: #6c757d; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #dee2e6; }}
                th {{ background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Cloud Billing Alert</h1>
                    <span class="severity">{alert.severity.value.upper()}</span>
                </div>
                <div class="content">
                    <h2>{alert.title}</h2>
                    <p>{alert.description}</p>
                    
                    <div class="metadata">
                        <h3>Alert Details</h3>
                        <table>
                            <tr><th>Alert ID</th><td>{alert.id}</td></tr>
                            <tr><th>Source</th><td>{alert.source}</td></tr>
                            <tr><th>Timestamp</th><td>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
                            <tr><th>Status</th><td>{alert.status.value}</td></tr>
                        </table>
                    </div>
                    
                    {self._format_metadata(alert.metadata) if alert.metadata else ''}
                    
                    {self._format_template_data(template_data) if template_data else ''}
                </div>
                <div class="footer">
                    <p>This alert was generated by Cloud Billing Automation Tool.</p>
                    <p>If you believe this is a false positive, please acknowledge the alert in the dashboard.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for HTML display."""
        if not metadata:
            return ""
        
        html = '<div class="metadata"><h3>Additional Information</h3><table>'
        for key, value in metadata.items():
            html += f'<tr><th>{key}</th><td>{value}</td></tr>'
        html += '</table></div>'
        
        return html
    
    def _format_template_data(self, template_data: Dict[str, Any]) -> str:
        """Format template data for HTML display."""
        if not template_data:
            return ""
        
        html = '<div class="metadata"><h3>Context Information</h3><table>'
        for key, value in template_data.items():
            html += f'<tr><th>{key}</th><td>{value}</td></tr>'
        html += '</table></div>'
        
        return html


class WebhookChannel(BaseChannel):
    """Webhook notification channel."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get('url')
        self.method = config.get('method', 'POST').upper()
        self.headers = config.get('headers', {})
        self.timeout = config.get('timeout', 30)
        self.retry_count = config.get('retry_count', 3)
    
    def send(self, alert: Alert, template_data: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert via webhook."""
        try:
            if not self.is_enabled():
                return False
            
            # Prepare payload
            payload = {
                'alert': alert.to_dict(),
                'template_data': template_data or {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Send webhook
            for attempt in range(self.retry_count):
                try:
                    response = requests.request(
                        method=self.method,
                        url=self.url,
                        json=payload,
                        headers=self.headers,
                        timeout=self.timeout
                    )
                    
                    if response.status_code < 400:
                        return True
                    
                except requests.exceptions.RequestException:
                    if attempt == self.retry_count - 1:
                        raise
                    continue
            
            return False
            
        except Exception as e:
            raise AlertError(f"Failed to send webhook alert: {e}")
    
    def test_connection(self) -> bool:
        """Test webhook connection."""
        try:
            test_payload = {
                'test': True,
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.request(
                method=self.method,
                url=self.url,
                json=test_payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            return response.status_code < 400
            
        except Exception:
            return False


class SlackChannel(BaseChannel):
    """Slack notification channel."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel')
        self.username = config.get('username', 'CloudBillingBot')
        self.icon_emoji = config.get('icon_emoji', ':robot_face:')
        self.timeout = config.get('timeout', 30)
    
    def send(self, alert: Alert, template_data: Optional[Dict[str, Any]] = None) -> bool:
        """Send alert via Slack."""
        try:
            if not self.is_enabled():
                return False
            
            # Create Slack message
            message = self._create_slack_message(alert, template_data)
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=self.timeout
            )
            
            return response.status_code == 200
            
        except Exception as e:
            raise AlertError(f"Failed to send Slack alert: {e}")
    
    def test_connection(self) -> bool:
        """Test Slack webhook connection."""
        try:
            test_message = {
                'text': '🧪 Cloud Billing Alert System Test',
                'username': self.username,
                'icon_emoji': self.icon_emoji
            }
            
            if self.channel:
                test_message['channel'] = self.channel
            
            response = requests.post(
                self.webhook_url,
                json=test_message,
                timeout=self.timeout
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def _create_slack_message(self, alert: Alert, template_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create Slack message payload."""
        severity_colors = {
            'low': 'good',
            'medium': 'warning',
            'high': 'danger',
            'critical': 'danger'
        }
        
        color = severity_colors.get(alert.severity.value, 'good')
        
        # Create attachment
        attachment = {
            'color': color,
            'title': f"{alert.title}",
            'text': alert.description,
            'fields': [
                {
                    'title': 'Severity',
                    'value': alert.severity.value.upper(),
                    'short': True
                },
                {
                    'title': 'Status',
                    'value': alert.status.value,
                    'short': True
                },
                {
                    'title': 'Source',
                    'value': alert.source,
                    'short': True
                },
                {
                    'title': 'Timestamp',
                    'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'short': True
                }
            ],
            'footer': 'Cloud Billing Automation',
            'ts': int(alert.timestamp.timestamp())
        }
        
        # Add metadata fields
        if alert.metadata:
            for key, value in list(alert.metadata.items())[:5]:  # Limit to 5 fields
                attachment['fields'].append({
                    'title': key,
                    'value': str(value),
                    'short': True
                })
        
        # Add template data fields
        if template_data:
            for key, value in list(template_data.items())[:3]:  # Limit to 3 fields
                attachment['fields'].append({
                    'title': key,
                    'value': str(value),
                    'short': True
                })
        
        message = {
            'username': self.username,
            'icon_emoji': self.icon_emoji,
            'attachments': [attachment]
        }
        
        if self.channel:
            message['channel'] = self.channel
        
        return message


class ChannelManager:
    """Manages multiple alert channels."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.channels: Dict[str, BaseChannel] = {}
        self._initialize_channels()
    
    def _initialize_channels(self) -> None:
        """Initialize all configured channels."""
        channels_config = self.config.get('channels', {})
        
        for channel_name, channel_config in channels_config.items():
            channel_type = channel_config.get('type')
            
            if channel_type == 'email':
                self.channels[channel_name] = EmailChannel(channel_config)
            elif channel_type == 'webhook':
                self.channels[channel_name] = WebhookChannel(channel_config)
            elif channel_type == 'slack':
                self.channels[channel_name] = SlackChannel(channel_config)
    
    def send_alert(self, alert: Alert, template_data: Optional[Dict[str, Any]] = None,
                  channel_names: Optional[List[str]] = None) -> Dict[str, bool]:
        """Send alert through specified channels or all enabled channels."""
        results = {}
        
        if channel_names:
            channels_to_use = {name: channel for name, channel in self.channels.items() 
                            if name in channel_names}
        else:
            channels_to_use = {name: channel for name, channel in self.channels.items() 
                            if channel.is_enabled()}
        
        for channel_name, channel in channels_to_use.items():
            try:
                results[channel_name] = channel.send(alert, template_data)
            except Exception as e:
                results[channel_name] = False
                # Log error but continue with other channels
                print(f"Failed to send alert via {channel_name}: {e}")
        
        return results
    
    def test_all_channels(self) -> Dict[str, bool]:
        """Test all channels."""
        results = {}
        
        for channel_name, channel in self.channels.items():
            results[channel_name] = channel.test_connection()
        
        return results
    
    def add_channel(self, name: str, channel: BaseChannel) -> None:
        """Add a new channel."""
        self.channels[name] = channel
    
    def remove_channel(self, name: str) -> None:
        """Remove a channel."""
        if name in self.channels:
            del self.channels[name]
    
    def get_channel(self, name: str) -> Optional[BaseChannel]:
        """Get a channel by name."""
        return self.channels.get(name)
    
    def list_channels(self) -> List[str]:
        """List all channel names."""
        return list(self.channels.keys())
