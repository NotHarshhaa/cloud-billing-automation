"""
Automated report scheduler and generator.
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import json
import logging
from enum import Enum
import threading

from ..core.config import Config
from ..core.exceptions import ReportError
from ..core.logging_config import get_logger
from ..collectors.base import BillingData
from ..analyzers.cost import CostAnalyzer
from ..analyzers.optimizer import CostOptimizer
from ..analyzers.ml_forecaster import BudgetForecaster

logger = get_logger(__name__)


class ReportFormat(Enum):
    """Report output formats."""
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"


class ReportSchedule(Enum):
    """Report scheduling frequencies."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass
class ReportConfig:
    """Configuration for automated reports."""
    name: str
    schedule: ReportSchedule
    format: ReportFormat
    recipients: List[str]
    include_charts: bool = True
    include_forecasts: bool = True
    include_optimizations: bool = True
    output_dir: str = "reports"
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


@dataclass
class GeneratedReport:
    """Generated report metadata."""
    name: str
    format: ReportFormat
    file_path: str
    generated_at: datetime
    file_size: int
    summary: Dict[str, Any]


class ReportScheduler:
    """Automated report scheduler and generator."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.reports: Dict[str, ReportConfig] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.report_generators: Dict[ReportFormat, Callable] = {
            ReportFormat.JSON: self._generate_json_report,
            ReportFormat.CSV: self._generate_csv_report,
            ReportFormat.HTML: self._generate_html_report,
        }
        
    def add_report(self, report_config: ReportConfig) -> None:
        """Add a new scheduled report."""
        try:
            # Calculate next run time
            report_config.next_run = self._calculate_next_run(report_config.schedule)
            
            self.reports[report_config.name] = report_config
            self.logger.info(f"Added scheduled report: {report_config.name} ({report_config.schedule.value})")
            
        except Exception as e:
            self.logger.error(f"Failed to add report {report_config.name}: {e}")
            raise ReportError(f"Failed to add report: {e}")
    
    def remove_report(self, report_name: str) -> None:
        """Remove a scheduled report."""
        if report_name in self.reports:
            del self.reports[report_name]
            self.logger.info(f"Removed scheduled report: {report_name}")
        else:
            self.logger.warning(f"Report not found: {report_name}")
    
    def start_scheduler(self) -> None:
        """Start the report scheduler."""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("Report scheduler started")
    
    def stop_scheduler(self) -> None:
        """Stop the report scheduler."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Report scheduler stopped")
    
    def _run_scheduler(self) -> None:
        """Run the scheduler loop."""
        while self.running:
            try:
                # Check for reports that need to run
                now = datetime.now()
                
                for report_name, report_config in self.reports.items():
                    if (report_config.enabled and 
                        report_config.next_run and 
                        now >= report_config.next_run):
                        
                        try:
                            self._generate_report(report_config)
                            report_config.last_run = now
                            report_config.next_run = self._calculate_next_run(report_config.schedule)
                            
                        except Exception as e:
                            self.logger.error(f"Failed to generate report {report_name}: {e}")
                
                # Sleep for 1 minute before next check
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _calculate_next_run(self, schedule: ReportSchedule) -> datetime:
        """Calculate the next run time for a schedule."""
        now = datetime.now()
        
        if schedule == ReportSchedule.DAILY:
            # Run at 9 AM tomorrow
            next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
                
        elif schedule == ReportSchedule.WEEKLY:
            # Run at 9 AM on Monday
            next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
            days_ahead = 0 - next_run.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
            
        elif schedule == ReportSchedule.MONTHLY:
            # Run at 9 AM on 1st of next month
            if now.month == 12:
                next_run = now.replace(year=now.year+1, month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
            else:
                next_run = now.replace(month=now.month+1, day=1, hour=9, minute=0, second=0, microsecond=0)
                
        elif schedule == ReportSchedule.QUARTERLY:
            # Run at 9 AM on 1st of next quarter
            current_quarter = (now.month - 1) // 3 + 1
            if current_quarter == 4:
                next_run = now.replace(year=now.year+1, month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
            else:
                next_month = current_quarter * 3 + 1
                next_run = now.replace(month=next_month, day=1, hour=9, minute=0, second=0, microsecond=0)
        else:
            next_run = now + timedelta(hours=1)
        
        return next_run
    
    def _generate_report(self, report_config: ReportConfig) -> GeneratedReport:
        """Generate a report."""
        try:
            self.logger.info(f"Generating report: {report_config.name}")
            
            # Collect data (this would need to be implemented based on your data collection)
            billing_data = self._collect_billing_data()
            resource_data = self._collect_resource_data()
            
            # Generate report content
            report_content = self._generate_report_content(
                billing_data, resource_data, report_config
            )
            
            # Save report in specified format
            generator = self.report_generators.get(report_config.format)
            if not generator:
                raise ReportError(f"Unsupported report format: {report_config.format}")
            
            file_path = generator(report_content, report_config)
            
            # Get file size
            file_size = Path(file_path).stat().st_size
            
            # Create report metadata
            report = GeneratedReport(
                name=report_config.name,
                format=report_config.format,
                file_path=file_path,
                generated_at=datetime.now(),
                file_size=file_size,
                summary=report_content.get('summary', {})
            )
            
            # Send report if recipients specified
            if report_config.recipients:
                self._send_report(report, report_config.recipients)
            
            self.logger.info(f"Report generated successfully: {file_path}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate report {report_config.name}: {e}")
            raise ReportError(f"Failed to generate report: {e}")
    
    def _collect_billing_data(self) -> List[BillingData]:
        """Collect billing data for reports."""
        # This is a placeholder - you would implement actual data collection
        # based on your existing collectors
        self.logger.info("Collecting billing data for report")
        return []
    
    def _collect_resource_data(self) -> List[Any]:
        """Collect resource data for reports."""
        # This is a placeholder - you would implement actual data collection
        self.logger.info("Collecting resource data for report")
        return []
    
    def _generate_report_content(self, billing_data: List[BillingData], 
                                resource_data: List[Any], 
                                report_config: ReportConfig) -> Dict[str, Any]:
        """Generate the main report content."""
        content = {
            "generated_at": datetime.now().isoformat(),
            "report_name": report_config.name,
            "period": {
                "start": (datetime.now() - timedelta(days=30)).isoformat(),
                "end": datetime.now().isoformat()
            }
        }
        
        # Cost analysis
        if billing_data:
            analyzer = CostAnalyzer(self.config)
            # This would need to be implemented based on your analyzer
            content["cost_analysis"] = {
                "total_cost": sum(b.cost for b in billing_data),
                "cost_trend": "increasing",
                "top_services": {}
            }
        
        # Optimization recommendations
        if report_config.include_optimizations and resource_data:
            optimizer = CostOptimizer(self.config)
            # This would need to be implemented based on your optimizer
            content["optimizations"] = {
                "recommendations": [],
                "potential_savings": 0.0
            }
        
        # Forecasting
        if report_config.include_forecasts and billing_data:
            forecaster = BudgetForecaster(self.config)
            # This would need to be implemented based on your forecaster
            content["forecast"] = {
                "next_30_days": 0.0,
                "confidence": 0.8
            }
        
        # Summary
        content["summary"] = {
            "total_cost": content.get("cost_analysis", {}).get("total_cost", 0),
            "potential_savings": content.get("optimizations", {}).get("potential_savings", 0),
            "forecast_next_month": content.get("forecast", {}).get("next_30_days", 0)
        }
        
        return content
    
    def _generate_json_report(self, content: Dict[str, Any], 
                             report_config: ReportConfig) -> str:
        """Generate JSON format report."""
        output_dir = Path(report_config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_config.name}_{timestamp}.json"
        file_path = output_dir / filename
        
        with open(file_path, 'w') as f:
            json.dump(content, f, indent=2, default=str)
        
        return str(file_path)
    
    def _generate_csv_report(self, content: Dict[str, Any], 
                            report_config: ReportConfig) -> str:
        """Generate CSV format report."""
        import pandas as pd
        
        output_dir = Path(report_config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_config.name}_{timestamp}.csv"
        file_path = output_dir / filename
        
        # Convert content to DataFrame (simplified)
        summary_data = content.get("summary", {})
        df = pd.DataFrame([summary_data])
        
        df.to_csv(file_path, index=False)
        
        return str(file_path)
    
    def _generate_html_report(self, content: Dict[str, Any], 
                             report_config: ReportConfig) -> str:
        """Generate HTML format report."""
        output_dir = Path(report_config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_config.name}_{timestamp}.html"
        file_path = output_dir / filename
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{content['report_name']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{content['report_name']}</h1>
                <p>Generated: {content['generated_at']}</p>
            </div>
            
            <div class="section">
                <h2>Summary</h2>
                <div class="metric">Total Cost: ${content.get('summary', {}).get('total_cost', 0):,.2f}</div>
                <div class="metric">Potential Savings: ${content.get('summary', {}).get('potential_savings', 0):,.2f}</div>
                <div class="metric">Forecast Next Month: ${content.get('summary', {}).get('forecast_next_month', 0):,.2f}</div>
            </div>
        </body>
        </html>
        """
        
        with open(file_path, 'w') as f:
            f.write(html_content)
        
        return str(file_path)
    
    def _send_report(self, report: GeneratedReport, recipients: List[str]) -> None:
        """Send report to recipients."""
        # This is a placeholder - you would implement email sending
        self.logger.info(f"Report {report.name} would be sent to {len(recipients)} recipients")
        for recipient in recipients:
            self.logger.debug(f"  - {recipient}")
    
    def get_scheduled_reports(self) -> Dict[str, ReportConfig]:
        """Get all scheduled reports."""
        return self.reports.copy()
    
    def get_report_status(self, report_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific report."""
        if report_name not in self.reports:
            return None
        
        config = self.reports[report_name]
        return {
            "name": config.name,
            "schedule": config.schedule.value,
            "format": config.format.value,
            "enabled": config.enabled,
            "last_run": config.last_run.isoformat() if config.last_run else None,
            "next_run": config.next_run.isoformat() if config.next_run else None,
            "recipients": config.recipients
        }
    
    def run_report_now(self, report_name: str) -> GeneratedReport:
        """Run a report immediately."""
        if report_name not in self.reports:
            raise ReportError(f"Report not found: {report_name}")
        
        report_config = self.reports[report_name]
        return self._generate_report(report_config)
