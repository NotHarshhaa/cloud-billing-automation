"""
Validation utilities for data validation and sanitization.
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from ..core.exceptions import CloudBillingError, ValidationError


class ValidationUtils:
    """Utilities for data validation and sanitization."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?$'
        return re.match(pattern, url) is not None
    
    @staticmethod
    def validate_aws_account_id(account_id: str) -> bool:
        """Validate AWS account ID format."""
        pattern = r'^\d{12}$'
        return re.match(pattern, account_id) is not None
    
    @staticmethod
    def validate_azure_subscription_id(subscription_id: str) -> bool:
        """Validate Azure subscription ID format."""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return re.match(pattern, subscription_id.lower()) is not None
    
    @staticmethod
    def validate_gcp_project_id(project_id: str) -> bool:
        """Validate GCP project ID format."""
        pattern = r'^[a-z][a-z0-9-]{4,28}[a-z0-9]$'
        return re.match(pattern, project_id) is not None
    
    @staticmethod
    def validate_resource_id(resource_id: str, provider: str) -> bool:
        """Validate resource ID format based on provider."""
        if provider == "aws":
            # AWS resource IDs vary by service
            return len(resource_id) > 0
        elif provider == "azure":
            # Azure resource IDs are longer
            return len(resource_id) > 0
        elif provider == "gcp":
            # GCP resource IDs vary by service
            return len(resource_id) > 0
        return False
    
    @staticmethod
    def validate_tag_key(tag_key: str) -> bool:
        """Validate tag key format."""
        # Most cloud providers have tag key restrictions
        if len(tag_key) > 128:
            return False
        
        # No invalid characters
        invalid_chars = ['<', '>', '&', '\\', '/', '"', '?']
        if any(char in tag_key for char in invalid_chars):
            return False
        
        return True
    
    @staticmethod
    def validate_tag_value(tag_value: str) -> bool:
        """Validate tag value format."""
        if len(tag_value) > 256:
            return False
        
        # No invalid characters
        invalid_chars = ['<', '>', '&', '\\', '/', '"', '?']
        if any(char in tag_value for char in invalid_chars):
            return False
        
        return True
    
    @staticmethod
    def validate_cost_amount(amount: Union[str, float, int]) -> bool:
        """Validate cost amount."""
        try:
            cost = float(amount)
            return cost >= 0 and cost < 1000000000  # Max 1 billion
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_percentage(percentage: Union[str, float, int]) -> bool:
        """Validate percentage (0-100)."""
        try:
            perc = float(percentage)
            return 0 <= perc <= 100
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> bool:
        """Validate date range."""
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            return start < end and (end - start) <= timedelta(days=365)
        except ValueError:
            return False
    
    @staticmethod
    def validate_region(region: str, provider: str) -> bool:
        """Validate region format for specific provider."""
        if provider == "aws":
            # AWS regions: us-east-1, eu-west-1, etc.
            pattern = r'^[a-z]{2}-[a-z]+-\d+$'
            return re.match(pattern, region) is not None
        elif provider == "azure":
            # Azure regions: eastus, westus2, etc.
            pattern = r'^[a-z]+[a-z\d]*$'
            return re.match(pattern, region) is not None
        elif provider == "gcp":
            # GCP regions: us-central1, us-east1, etc.
            pattern = r'^[a-z]+-\w+-\d+$'
            return re.match(pattern, region) is not None
        return False
    
    @staticmethod
    def validate_service_name(service: str, provider: str) -> bool:
        """Validate service name for specific provider."""
        if provider == "aws":
            # Common AWS services
            aws_services = [
                'Amazon EC2', 'Amazon RDS', 'Amazon S3', 'AWS Lambda',
                'Amazon CloudFront', 'Amazon Route 53', 'AWS CloudTrail',
                'Amazon VPC', 'Elastic Load Balancing', 'Amazon DynamoDB'
            ]
            return service in aws_services
        elif provider == "azure":
            # Common Azure services
            azure_services = [
                'Microsoft.Compute/virtualMachines',
                'Microsoft.Storage/storageAccounts',
                'Microsoft.Sql/servers',
                'Microsoft.Network/virtualNetworks',
                'Microsoft.Web/sites',
                'Microsoft.KeyVault/vaults'
            ]
            return service in azure_services
        elif provider == "gcp":
            # Common GCP services
            gcp_services = [
                'Compute Engine',
                'Cloud Storage',
                'Cloud SQL',
                'Cloud Functions',
                'Cloud Load Balancing',
                'Cloud DNS',
                'Cloud IAM',
                'Cloud Logging'
            ]
            return service in gcp_services
        
        # Generic validation
        return len(service) > 0 and len(service) <= 100
    
    @staticmethod
    def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate data against JSON schema."""
        errors = []
        
        for field, expected_type in schema.items():
            if field not in data:
                errors.append(f"Missing required field: {field}")
                continue
            
            value = data[field]
            
            # Type validation
            if expected_type == "string":
                if not isinstance(value, str):
                    errors.append(f"Field {field} must be a string")
            elif expected_type == "number":
                if not isinstance(value, (int, float)):
                    errors.append(f"Field {field} must be a number")
            elif expected_type == "boolean":
                if not isinstance(value, bool):
                    errors.append(f"Field {field} must be a boolean")
            elif expected_type == "array":
                if not isinstance(value, list):
                    errors.append(f"Field {field} must be an array")
            elif expected_type == "object":
                if not isinstance(value, dict):
                    errors.append(f"Field {field} must be an object")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_string(input_string: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not input_string:
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\'&\\]', '', input_string)
        
        # Limit length
        sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file system use."""
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
        
        # Replace spaces and other problematic characters
        sanitized = re.sub(r'\s+', '_', sanitized)
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Limit length
        sanitized = sanitized[:255]
        
        # Ensure not empty
        if not sanitized:
            sanitized = "unnamed"
        
        return sanitized
    
    @staticmethod
    def validate_file_path(file_path: str, check_exists: bool = False) -> bool:
        """Validate file path format."""
        try:
            path = Path(file_path)
            
            # Check for invalid characters
            invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
            if any(char in str(path) for char in invalid_chars):
                return False
            
            if check_exists and not path.exists():
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def validate_api_key(api_key: str, provider: str) -> bool:
        """Validate API key format for specific provider."""
        if provider == "aws":
            # AWS access keys are 20 characters long
            return len(api_key) == 20 and api_key.isalnum()
        elif provider == "azure":
            # Azure keys vary in format
            return len(api_key) >= 20
        elif provider == "gcp":
            # GCP service account keys are JSON
            try:
                json.loads(api_key)
                return True
            except json.JSONDecodeError:
                return False
        
        return len(api_key) >= 10
    
    @staticmethod
    def validate_budget_threshold(threshold: float) -> bool:
        """Validate budget threshold (0-1)."""
        return 0 < threshold <= 1
    
    @staticmethod
    def validate_currency(currency: str) -> bool:
        """Validate currency code."""
        valid_currencies = [
            'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY',
            'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN',
            'HRK', 'RUB', 'TRY', 'INR', 'SGD', 'HKD', 'NZD', 'ZAR',
            'MXN', 'BRL', 'ARS', 'CLP', 'COP', 'PEN', 'UYU', 'VES'
        ]
        return currency.upper() in valid_currencies
    
    @staticmethod
    def validate_cron_expression(cron_expr: str) -> bool:
        """Validate cron expression."""
        # Basic cron validation
        parts = cron_expr.split()
        if len(parts) != 5:
            return False
        
        # Validate each part
        patterns = [
            r'^\*|([0-9]|[1-5][0-9])$',  # minute
            r'^\*|([0-9]|[1-5][0-9])$',  # hour
            r'^\*|([1-9]|[1-2][0-9]|3[0-1])$',  # day of month
            r'^\*|([1-9]|1[0-2])$',  # month
            r'^\*|([0-6])$'  # day of week
        ]
        
        for part, pattern in zip(parts, patterns):
            if not re.match(pattern, part):
                return False
        
        return True
    
    @staticmethod
    def validate_webhook_url(url: str) -> bool:
        """Validate webhook URL."""
        return ValidationUtils.validate_url(url) and url.startswith(('http://', 'https://'))
    
    @staticmethod
    def validate_slack_webhook(webhook_url: str) -> bool:
        """Validate Slack webhook URL format."""
        return (webhook_url.startswith('https://hooks.slack.com/') or
                webhook_url.startswith('https://hooks.slack.com/services/'))
    
    @staticmethod
    def validate_configuration_structure(config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate overall configuration structure."""
        errors = []
        
        # Required top-level sections
        required_sections = ['providers', 'budget']
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Validate providers section
        if 'providers' in config:
            providers = config['providers']
            for provider in ['aws', 'azure', 'gcp']:
                if provider in providers:
                    provider_config = providers[provider]
                    
                    if provider == 'aws':
                        if 'account_id' in provider_config:
                            if not ValidationUtils.validate_aws_account_id(str(provider_config['account_id'])):
                                errors.append(f"Invalid AWS account ID: {provider_config['account_id']}")
                    
                    elif provider == 'azure':
                        if 'subscription_id' in provider_config:
                            if not ValidationUtils.validate_azure_subscription_id(str(provider_config['subscription_id'])):
                                errors.append(f"Invalid Azure subscription ID: {provider_config['subscription_id']}")
                    
                    elif provider == 'gcp':
                        if 'project_id' in provider_config:
                            if not ValidationUtils.validate_gcp_project_id(str(provider_config['project_id'])):
                                errors.append(f"Invalid GCP project ID: {provider_config['project_id']}")
        
        # Validate budget section
        if 'budget' in config:
            budget = config['budget']
            
            if 'monthly_limit' in budget:
                if not ValidationUtils.validate_cost_amount(budget['monthly_limit']):
                    errors.append(f"Invalid monthly budget limit: {budget['monthly_limit']}")
            
            if 'warning_threshold' in budget:
                if not ValidationUtils.validate_budget_threshold(budget['warning_threshold']):
                    errors.append(f"Invalid warning threshold: {budget['warning_threshold']}")
            
            if 'critical_threshold' in budget:
                if not ValidationUtils.validate_budget_threshold(budget['critical_threshold']):
                    errors.append(f"Invalid critical threshold: {budget['critical_threshold']}")
            
            if 'currency' in budget:
                if not ValidationUtils.validate_currency(budget['currency']):
                    errors.append(f"Invalid currency: {budget['currency']}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_billing_data(billing_data: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
        """Validate billing data structure."""
        errors = []
        
        required_fields = ['provider', 'account_id', 'service', 'cost', 'currency', 'timestamp']
        
        for i, data in enumerate(billing_data):
            for field in required_fields:
                if field not in data:
                    errors.append(f"Record {i}: Missing required field: {field}")
            
            if 'cost' in data:
                if not ValidationUtils.validate_cost_amount(data['cost']):
                    errors.append(f"Record {i}: Invalid cost amount: {data['cost']}")
            
            if 'currency' in data:
                if not ValidationUtils.validate_currency(data['currency']):
                    errors.append(f"Record {i}: Invalid currency: {data['currency']}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_alert_config(alert_config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate alert configuration."""
        errors = []
        
        # Check required fields
        if 'type' not in alert_config:
            errors.append("Missing alert type")
        
        if 'enabled' in alert_config:
            if not isinstance(alert_config['enabled'], bool):
                errors.append("Enabled field must be boolean")
        
        if 'severity' in alert_config:
            valid_severities = ['low', 'medium', 'high', 'critical']
            if alert_config['severity'] not in valid_severities:
                errors.append(f"Invalid severity: {alert_config['severity']}")
        
        if alert_config.get('type') == 'email':
            email_fields = ['smtp_server', 'username', 'from_email', 'to_emails']
            for field in email_fields:
                if field not in alert_config:
                    errors.append(f"Email alert missing required field: {field}")
            
            if 'to_emails' in alert_config:
                if not isinstance(alert_config['to_emails'], list):
                    errors.append("to_emails must be a list")
                else:
                    for email in alert_config['to_emails']:
                        if not ValidationUtils.validate_email(email):
                            errors.append(f"Invalid email address: {email}")
        
        elif alert_config.get('type') == 'webhook':
            if 'url' not in alert_config:
                errors.append("Webhook alert missing required field: url")
            elif not ValidationUtils.validate_webhook_url(alert_config['url']):
                errors.append(f"Invalid webhook URL: {alert_config['url']}")
        
        elif alert_config.get('type') == 'slack':
            if 'webhook_url' not in alert_config:
                errors.append("Slack alert missing required field: webhook_url")
            elif not ValidationUtils.validate_slack_webhook(alert_config['webhook_url']):
                errors.append(f"Invalid Slack webhook URL: {alert_config['webhook_url']}")
        
        return len(errors) == 0, errors
