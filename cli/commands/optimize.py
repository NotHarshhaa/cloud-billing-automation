"""
Optimization commands for cost recommendations.
"""

import typer
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn
import logging

from core.config import Config
from core.exceptions import CloudBillingError
from core.logging_config import get_logger
from analyzers.optimizer import CostOptimizer, CostRecommendation, RecommendationType
from collectors.base import BillingData, ResourceData

console = Console()
logger = get_logger(__name__)

# Create optimize app
app = typer.Typer(
    name="optimize",
    help="Cost optimization and recommendations",
    no_args_is_help=True
)


@app.command()
def analyze(
    start_date: Optional[datetime] = typer.Option(
        None,
        "--start-date",
        "-s",
        help="Start date for analysis (defaults to 30 days ago)",
        formats=["%Y-%m-%d"]
    ),
    end_date: Optional[datetime] = typer.Option(
        None,
        "--end-date",
        "-e",
        help="End date for analysis (defaults to now)",
        formats=["%Y-%m-%d"]
    ),
    providers: Optional[List[str]] = typer.Option(
        None,
        "--providers",
        "-p",
        help="Cloud providers to analyze (aws, azure, gcp)"
    ),
    min_savings: float = typer.Option(
        10.0,
        "--min-savings",
        help="Minimum potential savings to show recommendations"
    ),
    effort_level: Optional[str] = typer.Option(
        None,
        "--effort",
        help="Filter by effort level (low, medium, high)"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Analyze costs and generate optimization recommendations."""
    
    try:
        logger.info("Starting cost optimization analysis")
        
        # Load configuration
        config = _load_config(config_file)
        
        # Set default dates
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        console.print(f"[blue]🔍 Analyzing cost optimization opportunities from {start_date.date()} to {end_date.date()}...[/blue]")
        
        # Collect data with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Collecting data for optimization...", total=None)
            
            # This would need to be implemented based on your data collection
            billing_data = []  # _collect_billing_data(config, providers, start_date, end_date)
            resource_data = []  # _collect_resource_data(config, providers)
            
            progress.update(task, description="Analyzing optimization opportunities...")
        
        # Generate recommendations
        optimizer = CostOptimizer(config)
        recommendations = optimizer.analyze_costs_for_optimization(billing_data, resource_data)
        
        # Filter recommendations
        filtered_recommendations = _filter_recommendations(
            recommendations, min_savings, effort_level
        )
        
        if not filtered_recommendations:
            console.print("[green]✓ No optimization opportunities found[/green]")
            return
        
        # Display recommendations
        _display_recommendations(filtered_recommendations)
        
        # Generate summary report
        report = optimizer.generate_optimization_report(filtered_recommendations)
        _display_optimization_summary(report)
        
        logger.info(f"Optimization analysis completed with {len(filtered_recommendations)} recommendations")
        
    except CloudBillingError as e:
        logger.error(f"Cloud billing error: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in optimization analysis: {e}", exc_info=True)
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def quick_wins(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Show quick win opportunities (low effort, low risk)."""
    
    try:
        logger.info("Finding quick win optimization opportunities")
        
        # Load configuration
        config = _load_config(config_file)
        
        console.print("[blue]🎯 Finding quick win opportunities...[/blue]")
        
        # Collect data and analyze
        billing_data = []  # Would implement data collection
        resource_data = []  # Would implement resource collection
        
        optimizer = CostOptimizer(config)
        recommendations = optimizer.analyze_costs_for_optimization(billing_data, resource_data)
        
        # Filter for quick wins (low effort, low risk)
        quick_wins = [r for r in recommendations 
                     if r.effort_level == "low" and r.risk_level == "low"]
        
        if not quick_wins:
            console.print("[yellow]No quick win opportunities found[/yellow]")
            return
        
        # Sort by potential savings
        quick_wins.sort(key=lambda x: x.potential_savings, reverse=True)
        
        console.print(f"[green]Found {len(quick_wins)} quick win opportunities[/green]")
        _display_recommendations(quick_wins)
        
        total_savings = sum(r.potential_savings for r in quick_wins)
        console.print(f"\n[bold]Total Quick Win Savings: ${total_savings:,.2f}/month[/bold]")
        
    except Exception as e:
        logger.error(f"Error finding quick wins: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def by_type(
    recommendation_type: str = typer.Argument(
        ...,
        help="Type of recommendation (rightsizing, unused_resources, scheduled_shutdown, storage_optimization, reserved_instances, tag_compliance)"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration file path"
    )
) -> None:
    """Show recommendations by type."""
    
    try:
        # Convert string to enum
        try:
            rec_type = RecommendationType(recommendation_type)
        except ValueError:
            console.print(f"[red]Invalid recommendation type: {recommendation_type}[/red]")
            console.print("Valid types: rightsizing, unused_resources, scheduled_shutdown, storage_optimization, reserved_instances, tag_compliance")
            raise typer.Exit(1)
        
        logger.info(f"Finding {recommendation_type} recommendations")
        
        # Load configuration
        config = _load_config(config_file)
        
        console.print(f"[blue]🔍 Finding {recommendation_type} recommendations...[/blue]")
        
        # Collect data and analyze
        billing_data = []  # Would implement data collection
        resource_data = []  # Would implement resource collection
        
        optimizer = CostOptimizer(config)
        recommendations = optimizer.analyze_costs_for_optimization(billing_data, resource_data)
        
        # Filter by type
        type_recommendations = [r for r in recommendations if r.recommendation_type == rec_type]
        
        if not type_recommendations:
            console.print(f"[yellow]No {recommendation_type} recommendations found[/yellow]")
            return
        
        console.print(f"[green]Found {len(type_recommendations)} {recommendation_type} recommendations[/green]")
        _display_recommendations(type_recommendations)
        
    except Exception as e:
        logger.error(f"Error finding {recommendation_type} recommendations: {e}")
        console.print(f"[red]Error: {e}[/red]")
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


def _filter_recommendations(recommendations: List[CostRecommendation], 
                           min_savings: float, 
                           effort_level: Optional[str]) -> List[CostRecommendation]:
    """Filter recommendations based on criteria."""
    filtered = recommendations
    
    # Filter by minimum savings
    filtered = [r for r in filtered if r.potential_savings >= min_savings]
    
    # Filter by effort level
    if effort_level:
        filtered = [r for r in filtered if r.effort_level == effort_level]
    
    return filtered


def _display_recommendations(recommendations: List[CostRecommendation]) -> None:
    """Display optimization recommendations."""
    if not recommendations:
        return
    
    table = Table(title=f"Cost Optimization Recommendations ({len(recommendations)})")
    table.add_column("Title", style="cyan", max_width=30)
    table.add_column("Type", style="green")
    table.add_column("Savings", style="yellow")
    table.add_column("Effort", style="blue")
    table.add_column("Risk", style="red")
    table.add_column("Confidence", style="magenta")
    
    for rec in recommendations[:20]:  # Limit to 20 for display
        table.add_row(
            rec.title[:27] + "..." if len(rec.title) > 30 else rec.title,
            rec.recommendation_type.value,
            f"${rec.potential_savings:,.2f}",
            rec.effort_level,
            rec.risk_level,
            f"{rec.confidence_score:.1%}"
        )
    
    console.print(table)
    
    if len(recommendations) > 20:
        console.print(f"[dim]... and {len(recommendations) - 20} more recommendations[/dim]")


def _display_optimization_summary(report: dict) -> None:
    """Display optimization summary."""
    summary = report.get("summary", {})
    
    console.print("\n[bold]Optimization Summary:[/bold]")
    
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Total Recommendations", str(summary.get("total_recommendations", 0)))
    summary_table.add_row("Total Potential Savings", f"${summary.get('total_potential_savings', 0):,.2f}")
    summary_table.add_row("Average Savings per Recommendation", f"${summary.get('average_savings_per_recommendation', 0):,.2f}")
    
    console.print(summary_table)
    
    # Show top recommendation types
    by_type = report.get("recommendations_by_type", {})
    if by_type:
        console.print("\n[bold]Top Recommendation Types:[/bold]")
        type_table = Table()
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", style="green")
        type_table.add_column("Savings", style="yellow")
        
        sorted_types = sorted(by_type.items(), 
                            key=lambda x: x[1]["potential_savings"], 
                            reverse=True)
        
        for rec_type, data in sorted_types[:5]:
            type_table.add_row(
                rec_type.replace("_", " ").title(),
                str(data["count"]),
                f"${data['potential_savings']:,.2f}"
            )
        
        console.print(type_table)
