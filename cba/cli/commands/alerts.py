"""
Alerts commands for alert management and configuration.
"""

import typer
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from ...core.config import Config
from ...core.exceptions import CloudBillingError
from ...alerts.budget import BudgetAlertManager
from ...alerts.anomaly import AnomalyAlertManager
from ...alerts.channels import ChannelManager

console = Console()

# Create alerts app
app = typer.Typer(
    name="alerts",
    help="Alert management and configuration",
    no_args_is_help=True
)


@app.command()
def test(
    channels: Optional[List[str]] = typer.Option(
        None,
        "--channels",
        "-c",
        help="Specific channels to test (email, slack, webhook)"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-f",
        help="Configuration file path"
    )
) -> None:
    """Test alert notification channels."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        console.print("[blue]🧪 Testing alert channels...[/blue]")
        
        # Get notification configuration
        notifications = getattr(config, 'notifications', {})
        
        if not notifications:
            console.print("[red]No notification channels configured[/red]")
            console.print("Add notification channels to your configuration file.")
            return
        
        # Initialize channel manager
        channel_manager = ChannelManager(notifications)
        
        # Test channels
        if channels:
            # Test specific channels
            results = {}
            for channel_name in channels:
                channel = channel_manager.get_channel(channel_name)
                if channel:
                    console.print(f"  Testing {channel_name}...")
                    results[channel_name] = channel.test_connection()
                else:
                    console.print(f"  [red]Channel '{channel_name}' not found[/red]")
                    results[channel_name] = False
        else:
            # Test all channels
            console.print("Testing all configured channels...")
            results = channel_manager.test_all_channels()
        
        # Display results
        _display_test_results(results)
        
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
    severity: Optional[List[str]] = typer.Option(
        None,
        "--severity",
        "-s",
        help="Filter by severity (low, medium, high, critical)"
    ),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        help="Filter by status (active, resolved, acknowledged)"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-f",
        help="Configuration file path"
    )
) -> None:
    """Show alert history."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        console.print(f"[blue]📜 Loading alert history for last {days} days...[/blue]")
        
        # Get budget alert history
        budget_manager = BudgetAlertManager(config)
        budget_alerts = budget_manager.list_alerts()
        
        # Get anomaly alert history
        anomaly_manager = AnomalyAlertManager(config)
        anomaly_alerts = anomaly_manager.list_alerts()
        
        # Combine alerts
        all_alerts = budget_alerts + anomaly_alerts
        
        # Filter by date
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_alerts = [
            alert for alert in all_alerts 
            if alert.timestamp >= cutoff_date
        ]
        
        # Filter by severity
        if severity:
            recent_alerts = [
                alert for alert in recent_alerts 
                if alert.severity.value in severity
            ]
        
        # Filter by status
        if status:
            recent_alerts = [
                alert for alert in recent_alerts 
                if alert.status.value == status
            ]
        
        # Display alerts
        _display_alert_history(recent_alerts)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def suppress(
    resource_id: Optional[str] = typer.Option(
        None,
        "--resource-id",
        help="Resource ID to suppress alerts for"
    ),
    service: Optional[str] = typer.Option(
        None,
        "--service",
        help="Service to suppress alerts for"
    ),
    duration_hours: int = typer.Option(
        24,
        "--duration",
        "-d",
        help="Suppression duration in hours"
    ),
    reason: str = typer.Option(
        "Manual suppression",
        "--reason",
        help="Reason for suppression"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-f",
        help="Configuration file path"
    )
) -> None:
    """Suppress alerts for maintenance or other reasons."""
    
    try:
        if not resource_id and not service:
            console.print("[red]Error: Must specify either --resource-id or --service[/red]")
            raise typer.Exit(1)
        
        # Load configuration
        config = _load_config(config_file)
        
        console.print(f"[blue]🔇 Suppressing alerts for {duration_hours} hours...[/blue]")
        
        # Suppress anomaly alerts
        anomaly_manager = AnomalyAlertManager(config)
        success = anomaly_manager.suppress_anomaly(
            resource_id=resource_id,
            service=service,
            duration_hours=duration_hours,
            reason=reason
        )
        
        if success:
            console.print(Panel.fit(
                f"[bold green]✓ Alerts suppressed[/bold green]\n\n"
                f"Resource ID: {resource_id or 'N/A'}\n"
                f"Service: {service or 'N/A'}\n"
                f"Duration: {duration_hours} hours\n"
                f"Reason: {reason}\n"
                f"Expires: {(datetime.now() + timedelta(hours=duration_hours)).strftime('%Y-%m-%d %H:%M:%S')}",
                title="Alert Suppression",
                border_style="green"
            ))
        else:
            console.print("[red]Failed to suppress alerts[/red]")
            raise typer.Exit(1)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def acknowledge(
    alert_id: str = typer.Argument(..., help="Alert ID to acknowledge"),
    acknowledged_by: str = typer.Option(
        "cli-user",
        "--by",
        help="Name of person acknowledging"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-f",
        help="Configuration file path"
    )
) -> None:
    """Acknowledge an alert."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        console.print(f"[blue]👋 Acknowledging alert {alert_id}...[/blue]")
        
        # Try budget alerts first
        budget_manager = BudgetAlertManager(config)
        if budget_manager.acknowledge_alert(alert_id, acknowledged_by):
            console.print(f"[green]✓ Alert {alert_id} acknowledged by {acknowledged_by}[/green]")
            return
        
        # Try anomaly alerts
        anomaly_manager = AnomalyAlertManager(config)
        if anomaly_manager.acknowledge_alert(alert_id, acknowledged_by):
            console.print(f"[green]✓ Alert {alert_id} acknowledged by {acknowledged_by}[/green]")
            return
        
        console.print(f"[red]Alert {alert_id} not found[/red]")
        raise typer.Exit(1)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def resolve(
    alert_id: str = typer.Argument(..., help="Alert ID to resolve"),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-f",
        help="Configuration file path"
    )
) -> None:
    """Resolve an alert."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        console.print(f"[blue]✅ Resolving alert {alert_id}...[/blue]")
        
        # Try budget alerts first
        budget_manager = BudgetAlertManager(config)
        if budget_manager.resolve_alert(alert_id):
            console.print(f"[green]✓ Alert {alert_id} resolved[/green]")
            return
        
        # Try anomaly alerts
        anomaly_manager = AnomalyAlertManager(config)
        if anomaly_manager.resolve_alert(alert_id):
            console.print(f"[green]✓ Alert {alert_id} resolved[/green]")
            return
        
        console.print(f"[red]Alert {alert_id} not found[/red]")
        raise typer.Exit(1)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-f",
        help="Configuration file path"
    )
) -> None:
    """Show alert system status."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        console.print("[blue]📊 Alert System Status[/blue]")
        
        # Get budget alert statistics
        budget_manager = BudgetAlertManager(config)
        budget_stats = budget_manager.get_budget_statistics()
        
        # Get anomaly alert statistics
        anomaly_manager = AnomalyAlertManager(config)
        anomaly_stats = anomaly_manager.get_anomaly_statistics()
        
        # Display combined statistics
        _display_alert_status(budget_stats, anomaly_stats)
        
        # Show channel status
        notifications = getattr(config, 'notifications', {})
        if notifications:
            channel_manager = ChannelManager(notifications)
            channel_results = channel_manager.test_all_channels()
            _display_channel_status(channel_results)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def rules(
    list_rules: bool = typer.Option(
        True,
        "--list",
        help="List all alert rules"
    ),
    enable: Optional[str] = typer.Option(
        None,
        "--enable",
        help="Enable specific rule"
    ),
    disable: Optional[str] = typer.Option(
        None,
        "--disable", 
        help="Disable specific rule"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-f",
        help="Configuration file path"
    )
) -> None:
    """Manage alert rules."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        if enable:
            _toggle_rule(config, enable, True)
        elif disable:
            _toggle_rule(config, disable, False)
        elif list_rules:
            _list_alert_rules(config)
        
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


def _display_test_results(results: dict) -> None:
    """Display channel test results."""
    table = Table(title="Channel Test Results")
    table.add_column("Channel", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="dim")
    
    for channel_name, success in results.items():
        if success:
            status = "✓ Connected"
            status_color = "green"
            details = "Connection successful"
        else:
            status = "✗ Failed"
            status_color = "red"
            details = "Connection failed"
        
        table.add_row(channel_name, f"[{status_color}]{status}[/{status_color}]", details)
    
    console.print(table)
    
    # Summary
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    if success_count == total_count:
        console.print(f"\n[green]✓ All {total_count} channels working properly[/green]")
    else:
        console.print(f"\n[yellow]⚠ {success_count}/{total_count} channels working properly[/yellow]")


def _display_alert_history(alerts: List) -> None:
    """Display alert history."""
    if not alerts:
        console.print("[yellow]No alerts found matching criteria[/yellow]")
        return
    
    table = Table(title=f"Alert History ({len(alerts)} alerts)")
    table.add_column("ID", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Severity", style="red")
    table.add_column("Status", style="yellow")
    table.add_column("Source", style="blue")
    table.add_column("Time", style="green")
    
    for alert in alerts[:50]:  # Limit to 50 for display
        # Truncate ID for display
        display_id = alert.id[:8] + "..." if len(alert.id) > 8 else alert.id
        
        # Severity color
        severity_color = {
            'low': 'green',
            'medium': 'yellow',
            'high': 'orange',
            'critical': 'red'
        }.get(alert.severity.value, 'white')
        
        # Status color
        status_color = {
            'active': 'red',
            'acknowledged': 'yellow',
            'resolved': 'green',
            'suppressed': 'blue'
        }.get(alert.status.value, 'white')
        
        table.add_row(
            display_id,
            alert.title[:30] + "..." if len(alert.title) > 30 else alert.title,
            f"[{severity_color}]{alert.severity.value}[/{severity_color}]",
            f"[{status_color}]{alert.status.value}[/{status_color}]",
            alert.source,
            alert.timestamp.strftime("%Y-%m-%d %H:%M")
        )
    
    console.print(table)
    
    if len(alerts) > 50:
        console.print(f"[dim]... and {len(alerts) - 50} more alerts[/dim]")


def _display_alert_status(budget_stats: dict, anomaly_stats: dict) -> None:
    """Display alert system status."""
    # Combined statistics
    total_alerts = budget_stats['total_alerts'] + anomaly_stats['total_alerts']
    active_alerts = budget_stats['active_alerts'] + anomaly_stats['active_alerts']
    
    table = Table(title="Alert System Status")
    table.add_column("Category", style="cyan")
    table.add_column("Budget Alerts", style="green")
    table.add_column("Anomaly Alerts", style="blue")
    table.add_column("Total", style="yellow")
    
    table.add_row("Total Alerts", str(budget_stats['total_alerts']), str(anomaly_stats['total_alerts']), str(total_alerts))
    table.add_row("Active Alerts", str(budget_stats['active_alerts']), str(anomaly_stats['active_alerts']), str(active_alerts))
    table.add_row("Resolved Alerts", str(budget_stats['resolved_alerts']), str(anomaly_stats['resolved_alerts']), str(budget_stats['resolved_alerts'] + anomaly_stats['resolved_alerts']))
    table.add_row("Rules Configured", str(budget_stats['rules_configured']), str(anomaly_stats['rules_configured']), str(budget_stats['rules_configured'] + anomaly_stats['rules_configured']))
    
    console.print(table)


def _display_channel_status(channel_results: dict) -> None:
    """Display notification channel status."""
    table = Table(title="Notification Channels")
    table.add_column("Channel", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Status", style="green")
    
    for channel_name, success in channel_results.items():
        status = "✓ Online" if success else "✗ Offline"
        status_color = "green" if success else "red"
        table.add_row(channel_name, channel_name, f"[{status_color}]{status}[/{status_color}]")
    
    console.print(table)


def _toggle_rule(config: Config, rule_id: str, enable: bool) -> None:
    """Toggle alert rule enable/disable."""
    # This would require updating the configuration file
    # For now, just show what would happen
    action = "enable" if enable else "disable"
    console.print(f"[blue]Would {action} rule: {rule_id}[/blue]")
    console.print("[yellow]Rule toggle functionality requires configuration file update[/yellow]")


def _list_alert_rules(config: Config) -> None:
    """List all alert rules."""
    console.print("[blue]📋 Alert Rules[/blue]")
    
    # Budget alert rules
    budget_manager = BudgetAlertManager(config)
    budget_rules = budget_manager.list_rules()
    
    if budget_rules:
        console.print("\n[bold]Budget Alert Rules:[/bold]")
        table = Table()
        table.add_column("Rule ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Severity", style="red")
        table.add_column("Enabled", style="yellow")
        table.add_column("Cooldown", style="blue")
        
        for rule in budget_rules:
            enabled_status = "✓" if rule.enabled else "✗"
            enabled_color = "green" if rule.enabled else "red"
            table.add_row(
                rule.id,
                rule.name[:20] + "..." if len(rule.name) > 20 else rule.name,
                rule.severity.value,
                f"[{enabled_color}]{enabled_status}[/{enabled_color}]",
                f"{rule.cooldown_period}min"
            )
        
        console.print(table)
    
    # Anomaly alert rules
    anomaly_manager = AnomalyAlertManager(config)
    anomaly_rules = anomaly_manager.list_rules()
    
    if anomaly_rules:
        console.print("\n[bold]Anomaly Alert Rules:[/bold]")
        table = Table()
        table.add_column("Rule ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Severity", style="red")
        table.add_column("Enabled", style="yellow")
        table.add_column("Cooldown", style="blue")
        
        for rule in anomaly_rules:
            enabled_status = "✓" if rule.enabled else "✗"
            enabled_color = "green" if rule.enabled else "red"
            table.add_row(
                rule.id,
                rule.name[:20] + "..." if len(rule.name) > 20 else rule.name,
                rule.severity.value,
                f"[{enabled_color}]{enabled_status}[/{enabled_color}]",
                f"{rule.cooldown_period}min"
            )
        
        console.print(table)
