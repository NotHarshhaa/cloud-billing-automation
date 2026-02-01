"""
Analyze commands for cost analysis and insights.
"""

import typer
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import logging

from core.config import Config
from core.exceptions import CloudBillingError
from core.logging_config import get_logger
from collectors import AWSCollector, AzureCollector, GCPCollector
from analyzers.cost import CostAnalyzer
from analyzers.anomaly import AnomalyDetector
from analyzers.trend import TrendAnalyzer
from analyzers import CostForecaster

console = Console()
logger = get_logger(__name__)

# Create analyze app
app = typer.Typer(
    name="analyze",
    help="Analyze cloud costs and generate insights",
    no_args_is_help=True
)


@app.command()
def costs(
    start_date: datetime = typer.Option(
        ...,
        "--start-date",
        "-s",
        help="Start date for analysis (YYYY-MM-DD)",
        formats=["%Y-%m-%d"]
    ),
    end_date: datetime = typer.Option(
        ...,
        "--end-date", 
        "-e",
        help="End date for analysis (YYYY-MM-DD)",
        formats=["%Y-%m-%d"]
    ),
    providers: Optional[List[str]] = typer.Option(
        None,
        "--providers",
        "-p",
        help="Cloud providers to analyze (aws, azure, gcp)"
    ),
    output_format: str = typer.Option(
        "table",
        "--output",
        "-o",
        help="Output format (table, json, csv)"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Analyze costs for specified period."""
    
    try:
        logger.info(f"Starting cost analysis from {start_date.date()} to {end_date.date()}")
        
        # Load configuration
        config = _load_config(config_file)
        logger.debug("Configuration loaded successfully")
        
        # Validate date range
        if end_date <= start_date:
            error_msg = "End date must be after start date"
            logger.error(error_msg)
            console.print(f"[red]Error: {error_msg}[/red]")
            raise typer.Exit(1)
        
        if (end_date - start_date).days > 365:
            error_msg = "Date range cannot exceed 365 days"
            logger.error(error_msg)
            console.print(f"[red]Error: {error_msg}[/red]")
            raise typer.Exit(1)
        
        console.print(f"[blue]🔍 Analyzing costs from {start_date.date()} to {end_date.date()}...[/blue]")
        
        # Collect billing data with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Collecting billing data...", total=None)
            
            try:
                billing_data = _collect_billing_data(config, providers, start_date, end_date, progress)
                progress.update(task, description="Billing data collection complete")
            except Exception as e:
                progress.update(task, description=f"Error collecting data: {e}")
                raise
        
        if not billing_data:
            logger.warning("No billing data found for the specified period")
            console.print("[yellow]No billing data found for the specified period[/yellow]")
            return
        
        logger.info(f"Collected {len(billing_data)} billing records")
        
        # Analyze costs
        console.print("[blue]📊 Analyzing cost data...[/blue]")
        analyzer = CostAnalyzer(config)
        cost_summary = analyzer.analyze_costs(billing_data, start_date, end_date)
        
        # Display results
        _display_cost_summary(cost_summary, output_format)
        logger.info("Cost analysis completed successfully")
        
    except CloudBillingError as e:
        logger.error(f"Cloud billing error: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in cost analysis: {e}", exc_info=True)
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def breakdown(
    group_by: str = typer.Option(
        "service",
        "--group-by",
        "-g",
        help="Group by field (service, region, environment, cost_center)"
    ),
    period: str = typer.Option(
        "monthly",
        "--period",
        help="Analysis period (daily, weekly, monthly)"
    ),
    start_date: Optional[datetime] = typer.Option(
        None,
        "--start-date",
        "-s",
        help="Start date (defaults to 30 days ago)",
        formats=["%Y-%m-%d"]
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Get cost breakdown by specified grouping."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        # Set default start date
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        console.print(f"[blue]📊 Generating cost breakdown by {group_by}...[/blue]")
        
        # Collect billing data
        billing_data = _collect_billing_data(config, None, start_date, end_date)
        
        if not billing_data:
            console.print("[yellow]No billing data found[/yellow]")
            return
        
        # Get cost breakdown
        analyzer = CostAnalyzer(config)
        breakdown = analyzer.get_cost_breakdown(billing_data, start_date, end_date, group_by)
        
        # Display breakdown
        _display_cost_breakdown(breakdown, group_by)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def anomalies(
    methods: List[str] = typer.Option(
        ["zscore", "iqr", "percentage"],
        "--methods",
        "-m",
        help="Anomaly detection methods"
    ),
    threshold: float = typer.Option(
        2.0,
        "--threshold",
        "-t",
        help="Anomaly threshold multiplier"
    ),
    start_date: Optional[datetime] = typer.Option(
        None,
        "--start-date",
        "-s",
        help="Start date (defaults to 30 days ago)",
        formats=["%Y-%m-%d"]
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Detect cost anomalies."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        # Set default start date
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        console.print(f"[blue]🔍 Detecting anomalies using methods: {', '.join(methods)}...[/blue]")
        
        # Collect billing data
        billing_data = _collect_billing_data(config, None, start_date, end_date)
        
        if not billing_data:
            console.print("[yellow]No billing data found[/yellow]")
            return
        
        # Detect anomalies
        detector = AnomalyDetector(config)
        anomalies = detector.detect_anomalies(billing_data, methods)
        
        # Display anomalies
        _display_anomalies(anomalies)
        
    except CloudBillingError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def trends(
    metrics: List[str] = typer.Option(
        ["total_cost"],
        "--metrics",
        help="Trend metrics to analyze"
    ),
    period: str = typer.Option(
        "monthly",
        "--period",
        help="Analysis period (daily, weekly, monthly)"
    ),
    start_date: Optional[datetime] = typer.Option(
        None,
        "--start-date",
        "-s",
        help="Start date (defaults to 90 days ago)",
        formats=["%Y-%m-%d"]
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Analyze cost trends."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        # Set default start date
        if not start_date:
            start_date = datetime.now() - timedelta(days=90)
        end_date = datetime.now()
        
        console.print(f"[blue]📈 Analyzing cost trends...[/blue]")
        
        # Collect billing data
        billing_data = _collect_billing_data(config, None, start_date, end_date)
        
        if not billing_data:
            console.print("[yellow]No billing data found[/yellow]")
            return
        
        # Analyze trends
        analyzer = TrendAnalyzer(config)
        trends = analyzer.analyze_trends(billing_data, metrics)
        
        # Display trends
        _display_trends(trends)
        
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
        help="Number of days to forecast"
    ),
    model: str = typer.Option(
        "auto",
        "--model",
        help="Forecasting model (linear, random_forest, auto)"
    ),
    start_date: Optional[datetime] = typer.Option(
        None,
        "--start-date",
        "-s",
        help="Start date for training data (defaults to 60 days ago)",
        formats=["%Y-%m-%d"]
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Generate cost forecast."""
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        # Set default start date
        if not start_date:
            start_date = datetime.now() - timedelta(days=60)
        end_date = datetime.now()
        
        console.print(f"[blue]🔮 Generating {days}-day cost forecast...[/blue]")
        
        # Collect billing data
        billing_data = _collect_billing_data(config, None, start_date, end_date)
        
        if not billing_data:
            console.print("[yellow]No billing data found[/yellow]")
            return
        
        # Generate forecast
        if CostForecaster is None:
            console.print("[yellow]Warning: CostForecaster not available - missing sklearn[/yellow]")
            return
        
        forecaster = CostForecaster(config)
        forecast = forecaster.forecast_costs(billing_data, days, model)
        
        # Display forecast
        _display_forecast(forecast)
        
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


def _collect_billing_data(config: Config, providers: Optional[List[str]], 
                          start_date: datetime, end_date: datetime, 
                          progress: Optional[Any] = None) -> List:
    """Collect billing data from specified providers."""
    all_data = []
    
    # Determine which providers to use
    if providers:
        provider_list = providers
        logger.info(f"Using specified providers: {', '.join(providers)}")
    else:
        provider_list = []
        if config.aws.enabled:
            provider_list.append("aws")
        if config.azure.enabled:
            provider_list.append("azure")
        if config.gcp.enabled:
            provider_list.append("gcp")
        logger.info(f"Using enabled providers: {', '.join(provider_list)}")
    
    # Collect data from each provider
    for provider in provider_list:
        try:
            logger.debug(f"Collecting data from {provider.upper()}")
            if progress:
                progress.update(progress.tasks[0], description=f"Collecting from {provider.upper()}...")
            else:
                console.print(f"  [dim]Collecting data from {provider.upper()}...[/dim]")
            
            if provider == "aws":
                # Check if AWS collector is available
                if AWSCollector is None:
                    console.print("[yellow]Warning: AWS collector not available - missing boto3[/yellow]")
                    continue
                    
                # Get AWS credentials
                from core.credentials import CredentialManager
                cred_mgr = CredentialManager()
                aws_creds = cred_mgr.get_aws_credentials()
                
                if not aws_creds:
                    logger.warning("AWS credentials not configured")
                    console.print(f"[yellow]Warning: AWS credentials not configured[/yellow]")
                    continue
                
                collector = AWSCollector(config, aws_creds)
                collector.authenticate()
                data = collector.collect_billing_data(start_date, end_date)
                all_data.extend(data)
                logger.info(f"Collected {len(data)} AWS billing records")
                
            elif provider == "azure":
                # Check if Azure collector is available
                if AzureCollector is None:
                    console.print("[yellow]Warning: Azure collector not available - missing azure modules[/yellow]")
                    continue
                    
                # Get Azure credentials
                from core.credentials import CredentialManager
                cred_mgr = CredentialManager()
                azure_creds = cred_mgr.get_azure_credentials()
                
                if not azure_creds:
                    logger.warning("Azure credentials not configured")
                    console.print(f"[yellow]Warning: Azure credentials not configured[/yellow]")
                    continue
                
                collector = AzureCollector(config, azure_creds)
                collector.authenticate()
                data = collector.collect_billing_data(start_date, end_date)
                all_data.extend(data)
                logger.info(f"Collected {len(data)} Azure billing records")
                
            elif provider == "gcp":
                # Check if GCP collector is available
                if GCPCollector is None:
                    console.print("[yellow]Warning: GCP collector not available - missing google cloud modules[/yellow]")
                    continue
                    
                # Get GCP credentials
                from core.credentials import CredentialManager
                cred_mgr = CredentialManager()
                gcp_creds = cred_mgr.get_gcp_credentials()
                
                if not gcp_creds:
                    logger.warning("GCP credentials not configured")
                    console.print(f"[yellow]Warning: GCP credentials not configured[/yellow]")
                    continue
                
                collector = GCPCollector(config, gcp_creds)
                collector.authenticate()
                data = collector.collect_billing_data(start_date, end_date)
                all_data.extend(data)
                logger.info(f"Collected {len(data)} GCP billing records")
                
        except Exception as e:
            logger.error(f"Failed to collect data from {provider}: {e}", exc_info=True)
            console.print(f"[yellow]Warning: Failed to collect data from {provider}: {e}[/yellow]")
            continue
    
    logger.info(f"Total billing records collected: {len(all_data)}")
    return all_data


def _display_cost_summary(summary, output_format: str) -> None:
    """Display cost summary in specified format."""
    if output_format == "json":
        import json
        rprint(json.dumps({
            'total_cost': summary.total_cost,
            'currency': summary.currency,
            'period_start': summary.period_start.isoformat(),
            'period_end': summary.period_end.isoformat(),
            'cost_by_service': summary.cost_by_service,
            'cost_by_region': summary.cost_by_region,
            'top_resources': summary.top_resources
        }, indent=2))
    else:
        # Table format
        table = Table(title=f"Cost Summary ({summary.currency})")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Cost", f"${summary.total_cost:,.2f}")
        table.add_row("Period", f"{summary.period_start.date()} to {summary.period_end.date()}")
        table.add_row("Services", str(len(summary.cost_by_service)))
        table.add_row("Regions", str(len(summary.cost_by_region)))
        
        console.print(table)
        
        # Top services
        if summary.cost_by_service:
            console.print("\n[bold]Top Services:[/bold]")
            service_table = Table()
            service_table.add_column("Service", style="cyan")
            service_table.add_column("Cost", style="green")
            service_table.add_column("Percentage", style="yellow")
            
            total_cost = summary.total_cost
            for service, cost in sorted(summary.cost_by_service.items(), key=lambda x: x[1], reverse=True)[:10]:
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                service_table.add_row(service, f"${cost:,.2f}", f"{percentage:.1f}%")
            
            console.print(service_table)


def _display_cost_breakdown(breakdown: dict, group_by: str) -> None:
    """Display cost breakdown."""
    if not breakdown:
        console.print("[yellow]No breakdown data available[/yellow]")
        return
    
    table = Table(title=f"Cost Breakdown by {group_by.title()}")
    table.add_column(group_by.title(), style="cyan")
    table.add_column("Cost", style="green")
    table.add_column("Percentage", style="yellow")
    
    total_cost = sum(breakdown.values())
    
    for key, cost in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
        percentage = (cost / total_cost * 100) if total_cost > 0 else 0
        table.add_row(key, f"${cost:,.2f}", f"{percentage:.1f}%")
    
    console.print(table)


def _display_anomalies(anomalies: List) -> None:
    """Display detected anomalies."""
    if not anomalies:
        console.print("[green]✓ No anomalies detected[/green]")
        return
    
    table = Table(title=f"Detected Anomalies ({len(anomalies)})")
    table.add_column("Type", style="cyan")
    table.add_column("Severity", style="red")
    table.add_column("Resource", style="yellow")
    table.add_column("Service", style="blue")
    table.add_column("Deviation", style="green")
    table.add_column("Confidence", style="magenta")
    
    for anomaly in anomalies[:20]:  # Limit to 20 for display
        severity_color = {
            'low': 'green',
            'medium': 'yellow', 
            'high': 'orange',
            'critical': 'red'
        }.get(anomaly.severity, 'white')
        
        table.add_row(
            anomaly.anomaly_type,
            f"[{severity_color}]{anomaly.severity}[/{severity_color}]",
            anomaly.resource_id[:20] + "..." if len(anomaly.resource_id) > 20 else anomaly.resource_id,
            anomaly.service,
            f"+{anomaly.deviation_percentage:.1f}%",
            f"{anomaly.confidence_score:.2f}"
        )
    
    console.print(table)
    
    if len(anomalies) > 20:
        console.print(f"[dim]... and {len(anomalies) - 20} more anomalies[/dim]")


def _display_trends(trends: dict) -> None:
    """Display trend analysis."""
    if not trends:
        console.print("[yellow]No trend data available[/yellow]")
        return
    
    table = Table(title="Cost Trends")
    table.add_column("Metric", style="cyan")
    table.add_column("Direction", style="green")
    table.add_column("Strength", style="yellow")
    table.add_column("Change Rate", style="blue")
    table.add_column("Confidence", style="magenta")
    
    for metric, trend in trends.items():
        direction_color = {
            'increasing': 'red',
            'decreasing': 'green',
            'stable': 'blue',
            'volatile': 'orange'
        }.get(trend.trend_direction, 'white')
        
        table.add_row(
            metric,
            f"[{direction_color}]{trend.trend_direction}[/{direction_color}]",
            f"{trend.trend_strength:.2f}",
            f"${trend.change_rate:.2f}/day",
            f"{trend.confidence:.2f}"
        )
    
    console.print(table)


def _display_forecast(forecast) -> None:
    """Display cost forecast."""
    total_forecast = sum(forecast.forecast_values)
    
    table = Table(title=f"Cost Forecast ({len(forecast.forecast_values)} days)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Model", forecast.model_used)
    table.add_row("Total Forecast", f"${total_forecast:,.2f}")
    table.add_row("Daily Average", f"${total_forecast/len(forecast.forecast_values):,.2f}")
    table.add_row("Accuracy", f"{forecast.accuracy_metrics.get('mape', 0):.1f}%")
    
    console.print(table)
    
    # Show confidence intervals
    console.print("\n[bold]Forecast Summary:[/bold]")
    for i, (date, value) in enumerate(zip(forecast.forecast_dates[:7], forecast.forecast_values[:7])):
        console.print(f"  {date.date()}: ${value:,.2f}")
    
    if len(forecast.forecast_dates) > 7:
        console.print(f"  [dim]... and {len(forecast.forecast_dates) - 7} more days[/dim]")
