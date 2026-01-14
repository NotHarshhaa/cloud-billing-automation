"""
Budget commands for budget monitoring and management.
"""

import typer
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ...core.config import Config
from ...core.exceptions import CloudBillingError
from ...alerts.budget import BudgetAlertManager
from ...analyzers.cost import CostAnalyzer

console = Console()

# Create budget app
app = typer.Typer(
    name="budget",
    help="Budget monitoring and management",
    no_args_is_help=True
)


@app.command()
def status(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    ),
    forecast: bool = typer.Option(
        False,
        "--forecast",
        "-f",
        help="Include budget forecast"
    )
) -> None:
    """Show current budget status."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        console.print("[blue]💰 Checking budget status...[/blue]")
        
        # Get current cost data
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now()
        
        # Collect billing data
        billing_data = _collect_recent_billing_data(config, start_date, end_date)
        
        if not billing_data:
            console.print("[yellow]No billing data found for current month[/yellow]")
            return
        
        # Analyze costs
        analyzer = CostAnalyzer(config)
        cost_summary = analyzer.analyze_costs(billing_data, start_date, end_date)
        
        # Get budget status
        budget_manager = BudgetAlertManager(config)
        budget_status = budget_manager.get_budget_status(cost_summary)
        
        # Display budget status
        _display_budget_status(budget_status, forecast)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def set_limit(
    limit: float = typer.Argument(..., help="Monthly budget limit"),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Set monthly budget limit."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        console.print(f"[blue]💰 Setting budget limit to ${limit:,.2f}...[/blue]")
        
        # Update budget limit
        config.budget.monthly_limit = limit
        
        # Save configuration
        if config_file:
            config_dict = config.to_dict()
            import yaml
            with open(config_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        
        console.print(Panel.fit(
            f"[bold green]✓ Budget limit updated[/bold green]\n\n"
            f"New monthly limit: ${limit:,.2f}\n"
            f"Warning threshold: ${limit * config.budget.warning_threshold:,.2f} ({config.budget.warning_threshold*100:.0f}%)\n"
            f"Critical threshold: ${limit * config.budget.critical_threshold:,.2f} ({config.budget.critical_threshold*100:.0f}%)",
            title="Budget Configuration",
            border_style="green"
        ))
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def alerts(
    setup: bool = typer.Option(
        False,
        "--setup",
        help="Set up budget alerts"
    ),
    test: bool = typer.Option(
        False,
        "--test",
        help="Test alert channels"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Manage budget alerts."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        if setup:
            _setup_budget_alerts(config)
        elif test:
            _test_alert_channels(config)
        else:
            _show_alert_status(config)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def history(
    days: int = typer.Option(
        30,
        "--days",
        "-d",
        help="Number of days of history to show"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Show budget alert history."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        # Get budget history
        budget_manager = BudgetAlertManager(config)
        history = budget_manager.get_budget_history(days)
        
        if not history:
            console.print("[yellow]No budget history found[/yellow]")
            return
        
        # Display history
        _display_budget_history(history)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def forecast(
    days: int = typer.Option(
        30,
        "--days",
        "-d",
        help="Forecast period in days"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Generate budget forecast."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        console.print(f"[blue]🔮 Generating {days}-day budget forecast...[/blue]")
        
        # Get current cost data
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now()
        
        # Collect billing data
        billing_data = _collect_recent_billing_data(config, start_date, end_date)
        
        if not billing_data:
            console.print("[yellow]No billing data found for current month[/yellow]")
            return
        
        # Analyze costs
        analyzer = CostAnalyzer(config)
        cost_summary = analyzer.analyze_costs(billing_data, start_date, end_date)
        
        # Generate forecast
        budget_manager = BudgetAlertManager(config)
        forecast_data = budget_manager.get_budget_forecast(cost_summary, days)
        
        # Display forecast
        _display_budget_forecast(forecast_data, config.budget.monthly_limit)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


def _load_config(config_file: Optional[Path]) -> Config:
    """Load configuration from file or environment."""
    if config_file:
        return Config.from_file(str(config_file))
    else:
        # Try to find default config file
        default_configs = [
            "config/billing-config.yaml",
            "billing-config.yaml",
            "~/.cba/billing-config.yaml"
        ]
        
        for config_path in default_configs:
            path = Path(config_path).expanduser()
            if path.exists():
                return Config.from_file(str(path))
        
        # Fall back to environment variables
        return Config.from_env()


def _collect_recent_billing_data(config: Config, start_date: datetime, end_date: datetime) -> List:
    """Collect recent billing data."""
    all_data = []
    
    # Try to collect from enabled providers
    if config.aws.enabled:
        try:
            from ...core.credentials import CredentialManager
            from ...collectors.aws_collector import AWSCollector
            
            cred_mgr = CredentialManager()
            aws_creds = cred_mgr.get_aws_credentials()
            
            if aws_creds:
                collector = AWSCollector(config, aws_creds)
                collector.authenticate()
                data = collector.collect_billing_data(start_date, end_date)
                all_data.extend(data)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to collect AWS data: {e}[/yellow]")
    
    # Similar for other providers...
    
    return all_data


def _display_budget_status(budget_status, include_forecast: bool) -> None:
    """Display budget status."""
    # Determine status color
    status_colors = {
        'healthy': 'green',
        'warning': 'yellow',
        'critical': 'orange',
        'exceeded': 'red'
    }
    status_color = status_colors.get(budget_status.status, 'white')
    
    # Main status table
    table = Table(title=f"Budget Status - {budget_status.status.title()}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Budget Limit", f"${budget_status.budget_limit:,.2f}")
    table.add_row("Current Spend", f"${budget_status.current_spend:,.2f}")
    table.add_row("Usage", f"[{status_color}]{budget_status.usage_percentage:.1f}%[/{status_color}]")
    table.add_row("Remaining", f"${budget_status.remaining_budget:,.2f}")
    table.add_row("Days Remaining", str(budget_status.days_remaining))
    
    if include_forecast and budget_status.forecasted_spend:
        forecast_percentage = (budget_status.forecasted_spend / budget_status.budget_limit * 100)
        forecast_color = 'green' if forecast_percentage < 80 else 'yellow' if forecast_percentage < 95 else 'red'
        table.add_row("Forecasted", f"[{forecast_color}]${budget_status.forecasted_spend:,.2f} ({forecast_percentage:.1f}%)[/{forecast_color}]")
    
    console.print(table)
    
    # Risk assessment
    risk_colors = {
        'low': 'green',
        'medium': 'yellow',
        'high': 'orange',
        'critical': 'red'
    }
    risk_color = risk_colors.get(budget_status.risk_level, 'white')
    
    console.print(Panel.fit(
        f"Risk Level: [{risk_color}]{budget_status.risk_level.upper()}[/{risk_color}]\n"
        f"Daily Average: ${budget_status.daily_average_spend:,.2f}\n"
        f"Projected Daily: ${budget_status.projected_daily_spend:,.2f}",
        title="Risk Assessment",
        border_style=risk_color
    ))


def _setup_budget_alerts(config: Config) -> None:
    """Set up budget alerts."""
    console.print("[blue]🔔 Setting up budget alerts...[/blue]")
    
    # Check if notification channels are configured
    notifications = getattr(config, 'notifications', {})
    channels = notifications.get('channels', {})
    
    if not channels:
        console.print("[red]No notification channels configured[/red]")
        console.print("Add notification channels to your configuration file:")
        console.print("""
notifications:
  channels:
    email:
      type: email
      smtp_server: smtp.company.com
      username: alerts@company.com
      to_emails: [devops@company.com]
        """)
        return
    
    # Test each channel
    from ...alerts.channels import ChannelManager
    channel_manager = ChannelManager(notifications)
    
    console.print("Testing notification channels...")
    test_results = channel_manager.test_all_channels()
    
    table = Table(title="Channel Test Results")
    table.add_column("Channel", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="dim")
    
    for channel_name, success in test_results.items():
        status = "✓ Connected" if success else "✗ Failed"
        status_color = "green" if success else "red"
        table.add_row(channel_name, f"[{status_color}]{status}[/{status_color}]", "")
    
    console.print(table)
    
    # Show alert rules
    console.print("\n[bold]Alert Rules:[/bold]")
    console.print(f"• Warning threshold: {config.budget.warning_threshold*100:.0f}%")
    console.print(f"• Critical threshold: {config.budget.critical_threshold*100:.0f}%")
    console.print(f"• Alert emails: {', '.join(config.budget.alert_emails)}")
    console.print(f"• Alert webhooks: {len(config.budget.alert_webhooks)} configured")


def _test_alert_channels(config: Config) -> None:
    """Test alert channels."""
    console.print("[blue]🧪 Testing alert channels...[/blue]")
    
    notifications = getattr(config, 'notifications', {})
    
    if not notifications:
        console.print("[red]No notification channels configured[/red]")
        return
    
    from ...alerts.channels import ChannelManager
    channel_manager = ChannelManager(notifications)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Testing channels...", total=None)
        
        test_results = channel_manager.test_all_channels()
        
        progress.update(task, description="Test complete")
    
    # Display results
    table = Table(title="Channel Test Results")
    table.add_column("Channel", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Status", style="green")
    
    for channel_name, success in test_results.items():
        channel = channel_manager.get_channel(channel_name)
        channel_type = channel.__class__.__name__.replace('Channel', '').lower()
        status = "✓ Success" if success else "✗ Failed"
        status_color = "green" if success else "red"
        table.add_row(channel_name, channel_type, f"[{status_color}]{status}[/{status_color}]")
    
    console.print(table)


def _show_alert_status(config: Config) -> None:
    """Show current alert status."""
    console.print("[blue]📊 Alert Status[/blue]")
    
    # Get budget manager
    budget_manager = BudgetAlertManager(config)
    stats = budget_manager.get_budget_statistics()
    
    # Display statistics
    table = Table(title="Alert Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Alerts", str(stats['total_alerts']))
    table.add_row("Active Alerts", str(stats['active_alerts']))
    table.add_row("Resolved Alerts", str(stats['resolved_alerts']))
    table.add_row("Budget Alerts", str(stats['budget_alerts_total']))
    table.add_row("Rules Configured", str(stats['rules_configured']))
    table.add_row("Rules Enabled", str(stats['rules_enabled']))
    
    console.print(table)
    
    # Show recent alerts
    recent_alerts = budget_manager.list_alerts()[:5]
    if recent_alerts:
        console.print("\n[bold]Recent Alerts:[/bold]")
        alerts_table = Table()
        alerts_table.add_column("Title", style="cyan")
        alerts_table.add_column("Severity", style="red")
        alerts_table.add_column("Time", style="yellow")
        
        for alert in recent_alerts:
            severity_color = {
                'low': 'green',
                'medium': 'yellow',
                'high': 'orange',
                'critical': 'red'
            }.get(alert.severity.value, 'white')
            
            alerts_table.add_row(
                alert.title,
                f"[{severity_color}]{alert.severity.value}[/{severity_color}]",
                alert.timestamp.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(alerts_table)


def _display_budget_history(history: List[dict]) -> None:
    """Display budget history."""
    table = Table(title=f"Budget History (Last {len(history)} entries)")
    table.add_column("Date", style="cyan")
    table.add_column("Usage", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Risk", style="red")
    
    for entry in reversed(history[-20:]):  # Show last 20 entries
        date = datetime.fromisoformat(entry['timestamp']).strftime("%Y-%m-%d %H:%M")
        usage = f"{entry['usage_percentage']:.1f}%"
        status = entry['status']
        risk = entry['risk_level']
        
        table.add_row(date, usage, status, risk)
    
    console.print(table)


def _display_budget_forecast(forecast_data: dict, budget_limit: float) -> None:
    """Display budget forecast."""
    current_spend = forecast_data['current_spend']
    forecasted_spend = forecast_data['forecasted_spend']
    daily_average = forecast_data['daily_average']
    
    # Calculate percentages
    current_percentage = (current_spend / budget_limit * 100) if budget_limit > 0 else 0
    forecast_percentage = (forecasted_spend / budget_limit * 100) if budget_limit > 0 else 0
    
    # Determine colors
    forecast_color = 'green' if forecast_percentage < 80 else 'yellow' if forecast_percentage < 95 else 'red'
    
    table = Table(title="Budget Forecast")
    table.add_column("Metric", style="cyan")
    table.add_column("Current", style="blue")
    table.add_column("Forecast", style="green")
    table.add_column("Budget", style="yellow")
    
    table.add_row("Total Spend", f"${current_spend:,.2f} ({current_percentage:.1f}%)", 
                  f"[{forecast_color}]${forecasted_spend:,.2f} ({forecast_percentage:.1f}%)[/{forecast_color}]", 
                  f"${budget_limit:,.2f}")
    table.add_row("Daily Average", f"${daily_average:,.2f}", 
                  f"${forecast_data.get('projected_daily', daily_average):,.2f}",
                  f"${budget_limit/30:,.2f}")
    
    console.print(table)
    
    # Trend information
    trend = forecast_data.get('trend', 'stable')
    confidence = forecast_data.get('confidence', 'medium')
    
    console.print(Panel.fit(
        f"Trend: {trend.title()}\n"
        f"Confidence: {confidence.title()}\n"
        f"Forecast Method: Linear Projection",
        title="Forecast Analysis",
        border_style="blue"
    ))
