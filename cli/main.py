"""
Main CLI application entry point.
"""

import typer
import rich
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from typing import Optional
from pathlib import Path

from ..core.config import Config
from ..core.exceptions import CloudBillingError

# Create console for rich output
console = Console()

# Create main app
app = typer.Typer(
    name="cba",
    help="🚨 Cloud Billing Automation - DevOps Cost Governance Tool",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False
)

# Add subcommands
from .commands import analyze, budget, alerts, resources, reports, credentials, config

app.add_typer(analyze.app, name="analyze", help="Analyze cloud costs and generate insights")
app.add_typer(budget.app, name="budget", help="Budget monitoring and management")
app.add_typer(alerts.app, name="alerts", help="Alert management and configuration")
app.add_typer(resources.app, name="resources", help="Resource inventory and optimization")
app.add_typer(reports.app, name="reports", help="Generate and manage reports")
app.add_typer(credentials.app, name="credentials", help="Manage cloud credentials")
app.add_typer(config.app, name="config", help="Configuration management")


@app.callback()
def main_callback(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output"
    )
) -> None:
    """Cloud Billing Automation CLI
    
    A comprehensive tool for DevOps engineers to monitor, analyze, and automate cloud billing across AWS, Azure, and GCP.
    
    Examples:
        cba analyze costs --start-date 2024-01-01 --end-date 2024-01-31
        cba budget status --config config/billing.yaml
        cba alerts test --channels email,slack
    """
    # Store global config for subcommands
    if config_file:
        try:
            cfg = Config.from_file(str(config_file))
            # Store in context for subcommands
            typer.ctx.ensure_object(dict)
            typer.ctx.obj['config'] = cfg
            typer.ctx.obj['config_file'] = config_file
        except CloudBillingError as e:
            console.print(f"[red]Error loading configuration: {e}[/red]")
            raise typer.Exit(1)
    
    # Set debug mode
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        typer.ctx.ensure_object(dict)
        typer.ctx.obj['debug'] = True
    
    # Set verbose mode
    if verbose:
        typer.ctx.ensure_object(dict)
        typer.ctx.obj['verbose'] = True


@app.command()
def version() -> None:
    """Show version information."""
    from .. import __version__, __author__
    
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Cloud Billing Automation", __version__)
    table.add_row("Author", __author__)
    table.add_row("Python", f"{typer.__version__}")
    
    console.print(table)


@app.command()
def status() -> None:
    """Show system status and configuration."""
    console.print(Panel.fit(
        "[bold green]🚨 Cloud Billing Automation[/bold green]\n\n"
        "System Status: [green]✓ Operational[/green]\n"
        "Configuration: [yellow]Not loaded[/yellow]\n"
        "Credentials: [yellow]Not configured[/yellow]",
        title="System Status",
        border_style="green"
    ))


@app.command()
def init(
    output_dir: Optional[Path] = typer.Option(
        Path("config"),
        "--output-dir",
        "-o",
        help="Output directory for configuration files"
    )
) -> None:
    """Initialize configuration files."""
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Create default configuration
    default_config = """# Cloud Billing Automation Configuration
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
    
    config_file = output_dir / "billing-config.yaml"
    config_file.write_text(default_config)
    
    # Create alerts configuration
    alerts_config = """# Alert Configuration
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
    min_confidence: 0.7
    min_deviation_percentage: 20.0
    channels: [email]

anomaly_detection:
  min_confidence: 0.7
  min_deviation_percentage: 20.0
  methods: [zscore, iqr, percentage]
"""
    
    alerts_file = output_dir / "alerts-config.yaml"
    alerts_file.write_text(alerts_config)
    
    console.print(Panel.fit(
        f"[bold green]✓ Configuration initialized[/bold green]\n\n"
        f"Created files:\n"
        f"• {config_file}\n"
        f"• {alerts_file}\n\n"
        f"[yellow]Next steps:[/yellow]\n"
        f"1. Edit configuration files with your settings\n"
        f"2. Set up credentials: cba credentials setup\n"
        f"3. Test configuration: cba config validate",
        title="Initialization Complete",
        border_style="green"
    ))


@app.command()
def doctor() -> None:
    """Run system diagnostics."""
    console.print("[bold blue]🔍 Running System Diagnostics...[/bold blue]")
    
    # Check Python version
    import sys
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # Check dependencies
    dependencies = {
        "typer": typer,
        "rich": rich,
        "yaml": None,
        "pandas": None,
        "boto3": None,
        "requests": None
    }
    
    missing_deps = []
    for dep, module in dependencies.items():
        try:
            if module is None:
                __import__(dep)
            console.print(f"  [green]✓[/green] {dep}")
        except ImportError:
            console.print(f"  [red]✗[/red] {dep}")
            missing_deps.append(dep)
    
    # Check configuration
    config_status = "[yellow]Not configured[/yellow]"
    try:
        config_files = [
            Path("config/billing-config.yaml"),
            Path("billing-config.yaml"),
            Path("~/.cba/billing-config.yaml").expanduser()
        ]
        
        for config_file in config_files:
            if config_file.exists():
                config_status = "[green]Found[/green]"
                break
    except Exception:
        pass
    
    # Check credentials
    cred_status = "[yellow]Not configured[/yellow]"
    try:
        from ..core.credentials import CredentialManager
        cred_mgr = CredentialManager()
        if cred_mgr.list_credentials():
            cred_status = "[green]Configured[/green]"
    except Exception:
        pass
    
    # Display results
    table = Table(title="System Health Check", show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")
    
    table.add_row("Python", f"[green]✓[/green]", python_version)
    table.add_row("Dependencies", 
                 "[green]✓[/green]" if not missing_deps else "[red]✗[/red]",
                 f"Missing: {', '.join(missing_deps)}" if missing_deps else "All installed")
    table.add_row("Configuration", config_status, "")
    table.add_row("Credentials", cred_status, "")
    
    console.print(table)
    
    if missing_deps:
        console.print(f"\n[red]Missing dependencies: {', '.join(missing_deps)}[/red]")
        console.print("Install with: [yellow]pip install cloud-billing-automation[/yellow]")
        raise typer.Exit(1)
    
    console.print("\n[bold green]✓ System diagnostics complete[/bold green]")


if __name__ == "__main__":
    app()
