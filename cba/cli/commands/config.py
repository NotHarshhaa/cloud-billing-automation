"""
Configuration commands for configuration management.
"""

import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich import print as rprint
import yaml
import os

from ...core.config import Config
from ...core.exceptions import CloudBillingError, ConfigurationError

console = Console()

# Create config app
app = typer.Typer(
    name="config",
    help="Configuration management",
    no_args_is_help=True
)


@app.command()
def validate(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Validate configuration file."""
    
    try:
        console.print("[blue]🔍 Validating configuration...[/blue]")
        
        # Load configuration
        if config_file:
            if not config_file.exists():
                console.print(f"[red]Error: Configuration file not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            config = Config.from_file(str(config_file))
            config_file_display = str(config_file)
        else:
            # Try to find default config file
            default_configs = [
                "config/billing-config.yaml",
                "billing-config.yaml",
                "~/.cba/billing-config.yaml"
            ]
            
            config = None
            config_file_display = "Not found"
            
            for config_path in default_configs:
                path = Path(config_path).expanduser()
                if path.exists():
                    config = Config.from_file(str(path))
                    config_file_display = str(path)
                    break
            
            if not config:
                config = Config.from_env()
                config_file_display = "Environment variables"
        
        # Validate configuration
        config.validate()
        
        # Display validation results
        table = Table(title="Configuration Validation")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")
        
        # Check providers
        provider_configs = [
            ("AWS", config.aws.enabled, config.aws.account_id),
            ("Azure", config.azure.enabled, config.azure.subscription_id),
            ("GCP", config.gcp.enabled, config.gcp.project_id)
        ]
        
        for provider_name, enabled, required_field in provider_configs:
            if enabled:
                if required_field:
                    status = "✓ Configured"
                    details = f"Required field present: {required_field}"
                else:
                    status = "⚠ Warning"
                    details = "Enabled but missing required field"
            else:
                status = "○ Disabled"
                details = "Provider is disabled"
            
            table.add_row(provider_name, status, details)
        
        # Check budget configuration
        if config.budget.monthly_limit > 0:
            budget_status = "✓ Configured"
            budget_details = f"Limit: ${config.budget.monthly_limit:.2f}"
        else:
            budget_status = "⚠ Warning"
            budget_details = "No budget limit set"
        
        table.add_row("Budget", budget_status, budget_details)
        
        # Check notification configuration
        notifications = getattr(config, 'notifications', {})
        if notifications:
            channels = notifications.get('channels', {})
            notification_status = "✓ Configured"
            notification_details = f"{len(channels)} channels configured"
        else:
            notification_status = "○ Not configured"
            notification_details = "No notification channels"
        
        table.add_row("Notifications", notification_status, notification_details)
        
        console.print(table)
        
        # Show configuration file location
        console.print(Panel.fit(
            f"Configuration Source: {config_file_display}\n"
            f"Debug Mode: {'Enabled' if config.debug else 'Disabled'}\n"
            f"Log Level: {config.log_level}\n"
            f"Data Retention: {config.data_retention_days} days",
            title="Configuration Summary",
            border_style="green"
        ))
        
        console.print("[green]✓ Configuration validation passed[/green]")
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration validation failed: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def show(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        help="Show specific section (providers, budget, notifications)"
    )
) -> None:
    """Show current configuration."""
    
    try:
        # Load configuration
        if config_file:
            config = Config.from_file(str(config_file))
        else:
            config = Config.from_env()
        
        if section:
            _show_config_section(config, section)
        else:
            _show_full_config(config)
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def create(
    output_file: Path = typer.Option(
        Path("billing-config.yaml"),
        "--output-file",
        "-o",
        help="Output configuration file path"
    ),
    template: str = typer.Option(
        "basic",
        "--template",
        help="Configuration template (basic, production, minimal)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing file"
    )
) -> None:
    """Create a new configuration file."""
    
    try:
        if output_file.exists() and not force:
            if not Confirm.ask(f"Configuration file {output_file} already exists. Overwrite?"):
                console.print("Operation cancelled")
                return
        
        console.print(f"[blue]📝 Creating configuration file: {output_file}[/blue]")
        
        # Create configuration based on template
        if template == "basic":
            config_content = _get_basic_template()
        elif template == "production":
            config_content = _get_production_template()
        elif template == "minimal":
            config_content = _get_minimal_template()
        else:
            console.print(f"[red]Error: Unknown template '{template}'. Use basic, production, or minimal.[/red]")
            raise typer.Exit(1)
        
        # Create output directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write configuration file
        output_file.write_text(config_content)
        
        console.print(Panel.fit(
            f"[bold green]✓ Configuration file created[/bold green]\n\n"
            f"File: {output_file}\n"
            f"Template: {template}\n\n"
            f"[yellow]Next steps:[/yellow]\n"
            f"1. Edit the configuration file with your settings\n"
            f"2. Validate: cba config validate --config {output_file}\n"
            f"3. Setup credentials: cba credentials setup",
            title="Configuration Created",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"[red]Error creating configuration file: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def edit(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        help="Edit specific section"
    )
) -> None:
    """Edit configuration interactively."""
    
    try:
        # Load configuration
        if config_file:
            if not config_file.exists():
                console.print(f"[red]Error: Configuration file not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            config = Config.from_file(str(config_file))
        else:
            # Find default config file
            default_configs = [
                "config/billing-config.yaml",
                "billing-config.yaml",
                "~/.cba/billing-config.yaml"
            ]
            
            config = None
            config_file = None
            
            for config_path in default_configs:
                path = Path(config_path).expanduser()
                if path.exists():
                    config = Config.from_file(str(path))
                    config_file = path
                    break
            
            if not config:
                console.print("[yellow]No configuration file found. Use 'cba config create' to create one.[/yellow]")
                return
        
        console.print(f"[blue]📝 Editing configuration: {config_file}[/blue]")
        
        if section:
            _edit_config_section(config, section, config_file)
        else:
            _interactive_config_edit(config, config_file)
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def merge(
    source_file: Path = typer.Argument(..., help="Source configuration file"),
    target_file: Path = typer.Option(
        Path("billing-config.yaml"),
        "--target-file",
        help="Target configuration file"
    ),
    strategy: str = typer.Option(
        "merge",
        "--strategy",
        help="Merge strategy (merge, overwrite, keep-existing)"
    )
) -> None:
    """Merge configuration files."""
    
    try:
        console.print(f"[blue]🔀 Merging configurations...[/blue]")
        
        if not source_file.exists():
            console.print(f"[red]Error: Source file not found: {source_file}[/red]")
            raise typer.Exit(1)
        
        # Load configurations
        source_config = Config.from_file(str(source_file))
        
        if target_file.exists():
            target_config = Config.from_file(str(target_file))
        else:
            target_config = Config()
        
        # Merge configurations based on strategy
        if strategy == "overwrite":
            merged_config = source_config
        elif strategy == "keep-existing":
            merged_config = target_config
        else:  # merge
            merged_config = _merge_configs(source_config, target_config)
        
        # Save merged configuration
        merged_dict = merged_config.to_dict()
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_file, 'w') as f:
            yaml.dump(merged_dict, f, default_flow_style=False)
        
        console.print(Panel.fit(
            f"[bold green]✓ Configurations merged[/bold green]\n\n"
            f"Source: {source_file}\n"
            f"Target: {target_file}\n"
            f"Strategy: {strategy}",
            title="Configuration Merge",
            border_style="green"
        ))
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


def _show_config_section(config: Config, section: str) -> None:
    """Show specific configuration section."""
    if section == "providers":
        table = Table(title="Provider Configuration")
        table.add_column("Provider", style="cyan")
        table.add_column("Enabled", style="green")
        table.add_column("Account/Project", style="yellow")
        table.add_column("Regions", style="blue")
        
        providers = [
            ("AWS", config.aws.enabled, config.aws.account_id, config.aws.regions),
            ("Azure", config.azure.enabled, config.azure.subscription_id, config.azure.regions),
            ("GCP", config.gcp.enabled, config.gcp.project_id, config.gcp.regions)
        ]
        
        for provider, enabled, account, regions in providers:
            enabled_status = "✓ Yes" if enabled else "○ No"
            account_display = account or "Not configured"
            regions_display = ", ".join(regions) if regions else "All"
            
            table.add_row(provider, enabled_status, account_display, regions_display)
        
        console.print(table)
        
    elif section == "budget":
        table = Table(title="Budget Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Monthly Limit", f"${config.budget.monthly_limit:.2f}")
        table.add_row("Warning Threshold", f"{config.budget.warning_threshold*100:.0f}%")
        table.add_row("Critical Threshold", f"{config.budget.critical_threshold*100:.0f}%")
        table.add_row("Currency", config.budget.currency)
        table.add_row("Alert Emails", ", ".join(config.budget.alert_emails))
        table.add_row("Alert Webhooks", f"{len(config.budget.alert_webhooks)} configured")
        
        console.print(table)
        
    elif section == "notifications":
        notifications = getattr(config, 'notifications', {})
        
        if not notifications:
            console.print("[yellow]No notification configuration found[/yellow]")
            return
        
        channels = notifications.get('channels', {})
        
        if channels:
            table = Table(title="Notification Channels")
            table.add_column("Channel", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Status", style="yellow")
            
            for channel_name, channel_config in channels.items():
                channel_type = channel_config.get('type', 'unknown')
                enabled = channel_config.get('enabled', True)
                status = "✓ Enabled" if enabled else "○ Disabled"
                
                table.add_row(channel_name, channel_type, status)
            
            console.print(table)
        
    else:
        console.print(f"[red]Unknown section: {section}[/red]")
        console.print("Available sections: providers, budget, notifications")


def _show_full_config(config: Config) -> None:
    """Show full configuration."""
    config_dict = config.to_dict()
    
    # Convert to YAML and display
    yaml_content = yaml.dump(config_dict, default_flow_style=False)
    
    console.print(Panel.fit(
        yaml_content,
        title="Current Configuration",
        border_style="blue"
    ))


def _edit_config_section(config: Config, section: str, config_file: Path) -> None:
    """Edit specific configuration section."""
    console.print(f"\n[bold]Editing {section} configuration:[/bold]")
    
    if section == "providers":
        # Edit AWS configuration
        config.aws.enabled = Confirm.ask("Enable AWS provider?", default=config.aws.enabled)
        if config.aws.enabled:
            config.aws.account_id = Prompt.ask("AWS Account ID", default=config.aws.account_id or "")
            regions_input = Prompt.ask("AWS Regions (comma-separated)", default=",".join(config.aws.regions))
            config.aws.regions = [r.strip() for r in regions_input.split(",") if r.strip()]
    
    elif section == "budget":
        # Edit budget configuration
        config.budget.monthly_limit = float(Prompt.ask("Monthly Budget Limit", default=str(config.budget.monthly_limit)))
        config.budget.warning_threshold = float(Prompt.ask("Warning Threshold (0-1)", default=str(config.budget.warning_threshold)))
        config.budget.critical_threshold = float(Prompt.ask("Critical Threshold (0-1)", default=str(config.budget.critical_threshold)))
        
        emails_input = Prompt.ask("Alert Emails (comma-separated)", default=",".join(config.budget.alert_emails))
        config.budget.alert_emails = [e.strip() for e in emails_input.split(",") if e.strip()]
    
    # Save configuration
    config_dict = config.to_dict()
    with open(config_file, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False)
    
    console.print(f"[green]✓ {section.title()} configuration updated[/green]")


def _interactive_config_edit(config: Config, config_file: Path) -> None:
    """Interactive configuration editing."""
    console.print("\n[bold]Interactive Configuration Editor[/bold]")
    console.print("Select a section to edit (or 'done' to finish):")
    
    while True:
        sections = ["providers", "budget", "notifications", "done"]
        choice = Prompt.ask("Section to edit", choices=sections, default="done")
        
        if choice == "done":
            break
        
        _edit_config_section(config, choice, config_file)
    
    # Save final configuration
    config_dict = config.to_dict()
    with open(config_file, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False)
    
    console.print("[green]✓ Configuration saved[/green]")


def _merge_configs(source: Config, target: Config) -> Config:
    """Merge two configurations."""
    merged = Config()
    
    # Merge basic settings
    merged.debug = source.debug if source.debug != Config().debug else target.debug
    merged.log_level = source.log_level if source.log_level != Config().log_level else target.log_level
    merged.data_retention_days = source.data_retention_days if source.data_retention_days != Config().data_retention_days else target.data_retention_days
    
    # Merge providers
    merged.aws.enabled = source.aws.enabled if source.aws.enabled != Config().aws.enabled else target.aws.enabled
    merged.aws.account_id = source.aws.account_id or target.aws.account_id
    merged.aws.regions = source.aws.regions if source.aws.regions else target.aws.regions
    merged.aws.tags_required = source.aws.tags_required if source.aws.tags_required else target.aws.tags_required
    
    merged.azure.enabled = source.azure.enabled if source.azure.enabled != Config().azure.enabled else target.azure.enabled
    merged.azure.subscription_id = source.azure.subscription_id or target.azure.subscription_id
    merged.azure.regions = source.azure.regions if source.azure.regions else target.azure.regions
    merged.azure.tags_required = source.azure.tags_required if source.azure.tags_required else target.azure.tags_required
    
    merged.gcp.enabled = source.gcp.enabled if source.gcp.enabled != Config().gcp.enabled else target.gcp.enabled
    merged.gcp.project_id = source.gcp.project_id or target.gcp.project_id
    merged.gcp.regions = source.gcp.regions if source.gcp.regions else target.gcp.regions
    merged.gcp.tags_required = source.gcp.tags_required if source.gcp.tags_required else target.gcp.tags_required
    
    # Merge budget
    merged.budget.monthly_limit = source.budget.monthly_limit if source.budget.monthly_limit != Config().budget.monthly_limit else target.budget.monthly_limit
    merged.budget.warning_threshold = source.budget.warning_threshold if source.budget.warning_threshold != Config().budget.warning_threshold else target.budget.warning_threshold
    merged.budget.critical_threshold = source.budget.critical_threshold if source.budget.critical_threshold != Config().budget.critical_threshold else target.budget.critical_threshold
    merged.budget.currency = source.budget.currency if source.budget.currency != Config().budget.currency else target.budget.currency
    merged.budget.alert_emails = source.budget.alert_emails if source.budget.alert_emails else target.budget.alert_emails
    merged.budget.alert_webhooks = source.budget.alert_webhooks if source.budget.alert_webhooks else target.budget.alert_webhooks
    
    return merged


def _get_basic_template() -> str:
    """Get basic configuration template."""
    return """# Cloud Billing Automation Configuration
debug: false
log_level: "INFO"
data_retention_days: 90

providers:
  aws:
    enabled: true
    account_id: "YOUR-AWS-ACCOUNT-ID"
    regions: ["us-east-1", "us-west-2"]
    tags_required: ["Environment", "CostCenter", "Owner"]
    cost_center_tag: "CostCenter"
    environment_tag: "Environment"
  
  azure:
    enabled: false
    subscription_id: "YOUR-AZURE-SUBSCRIPTION-ID"
    regions: ["eastus", "westus2"]
    tags_required: ["Environment", "CostCenter"]
  
  gcp:
    enabled: false
    project_id: "YOUR-GCP-PROJECT-ID"
    regions: ["us-central1", "us-east1"]
    tags_required: ["Environment", "CostCenter"]

budget:
  monthly_limit: 10000.0
  warning_threshold: 0.8
  critical_threshold: 0.95
  currency: "USD"
  alert_emails: ["devops@company.com"]
  alert_webhooks: []

reports:
  output_dir: "reports"
  formats: ["json", "csv", "html"]
  schedule: "daily"
  include_charts: true
  email_reports: false
  email_recipients: []

notifications:
  channels:
    email:
      type: email
      smtp_server: smtp.company.com
      smtp_port: 587
      username: alerts@company.com
      password: ${EMAIL_PASSWORD}
      from_email: alerts@company.com
      to_emails: [devops@company.com]
      use_tls: true
    
    slack:
      type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#billing-alerts"
      username: "CloudBillingBot"
      icon_emoji: ":moneybag:"
    
    webhook:
      type: webhook
      url: https://monitoring.company.com/webhooks/billing
      method: POST
      timeout: 30
      retry_count: 3
"""


def _get_production_template() -> str:
    """Get production configuration template."""
    return """# Production Cloud Billing Automation Configuration
debug: false
log_level: "WARNING"
data_retention_days: 365

providers:
  aws:
    enabled: true
    account_id: "PROD-AWS-ACCOUNT-ID"
    regions: ["us-east-1", "us-west-2", "eu-west-1"]
    tags_required: ["Environment", "CostCenter", "Owner", "Project"]
    cost_center_tag: "CostCenter"
    environment_tag: "Environment"
  
  azure:
    enabled: true
    subscription_id: "PROD-AZURE-SUBSCRIPTION-ID"
    regions: ["eastus", "westus2", "westeurope"]
    tags_required: ["Environment", "CostCenter", "Owner", "Project"]
  
  gcp:
    enabled: true
    project_id: "prod-gcp-project"
    regions: ["us-central1", "us-east1", "europe-west1"]
    tags_required: ["Environment", "CostCenter", "Owner", "Project"]

budget:
  monthly_limit: 50000.0
  warning_threshold: 0.75
  critical_threshold: 0.90
  currency: "USD"
  alert_emails: ["devops@company.com", "finance@company.com", "management@company.com"]
  alert_webhooks: ["https://monitoring.company.com/webhooks/billing", "https://hooks.slack.com/production"]

reports:
  output_dir: "/var/log/cloud-billing-automation/reports"
  formats: ["json", "html", "pdf"]
  schedule: "daily"
  include_charts: true
  email_reports: true
  email_recipients: ["finance@company.com", "management@company.com"]

notifications:
  channels:
    email:
      type: email
      smtp_server: smtp.company.com
      smtp_port: 587
      username: alerts@company.com
      password: ${EMAIL_PASSWORD}
      from_email: alerts@company.com
      to_emails: 
        - devops@company.com
        - finance@company.com
        - management@company.com
      use_tls: true
    
    slack:
      type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#billing-alerts"
      username: "CloudBillingBot"
      icon_emoji: ":moneybag:"
    
    webhook:
      type: webhook
      url: https://monitoring.company.com/webhooks/billing
      method: POST
      headers:
        Authorization: "Bearer ${WEBHOOK_TOKEN}"
        Content-Type: "application/json"
      timeout: 30
      retry_count: 3

  alert_rules:
    budget_warning:
      enabled: true
      severity: medium
      cooldown_period: 60
      channels: [email, slack]
    
    budget_critical:
      enabled: true
      severity: high
      cooldown_period: 30
      channels: [email, slack, webhook]
    
    anomaly_detection:
      enabled: true
      min_confidence: 0.8
      min_deviation_percentage: 15.0
      channels: [email, slack]
"""


def _get_minimal_template() -> str:
    """Get minimal configuration template."""
    return """# Minimal Cloud Billing Automation Configuration
debug: false
log_level: "INFO"

providers:
  aws:
    enabled: true
    account_id: "YOUR-AWS-ACCOUNT-ID"
    regions: ["us-east-1"]
    tags_required: ["Environment", "CostCenter"]
  
  azure:
    enabled: false
  
  gcp:
    enabled: false

budget:
  monthly_limit: 1000.0
  warning_threshold: 0.8
  critical_threshold: 0.95
  currency: "USD"
  alert_emails: ["admin@company.com"]
"""
