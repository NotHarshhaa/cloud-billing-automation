"""
Helper utilities for common operations.
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from ..core.exceptions import CloudBillingError


class FormatUtils:
    """Formatting utilities for data presentation."""
    
    @staticmethod
    def format_currency(amount: float, currency: str = "USD", 
                      include_symbol: bool = True) -> str:
        """Format currency amount."""
        if include_symbol:
            symbols = {
                'USD': '$',
                'EUR': '€',
                'GBP': '£',
                'JPY': '¥',
                'CAD': 'C$',
                'AUD': 'A$',
                'CHF': 'Fr',
                'CNY': '¥'
            }
            symbol = symbols.get(currency, currency)
            return f"{symbol}{amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
    
    @staticmethod
    def format_percentage(value: float, decimal_places: int = 1) -> str:
        """Format percentage value."""
        return f"{value:.{decimal_places}f}%"
    
    @staticmethod
    def format_number(number: Union[int, float], 
                       decimal_places: int = 2) -> str:
        """Format number with thousands separator."""
        if isinstance(number, int):
            return f"{number:,}"
        else:
            return f"{number:,.{decimal_places}f}"
    
    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """Format bytes in human readable format."""
        if bytes_value == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = int(math.floor(math.log(bytes_value, 1024)))
        
        if unit_index >= len(units):
            unit_index = len(units) - 1
        
        size = bytes_value / (1024 ** unit_index)
        
        if unit_index == 0:
            return f"{bytes_value} B"
        else:
            return f"{size:.1f} {units[unit_index]}"
    
    @staticmethod
    def format_duration(start_time: datetime, end_time: datetime) -> str:
        """Format duration between two timestamps."""
        duration = end_time - start_time
        
        if duration.days > 0:
            return f"{duration.days}d {duration.seconds // 3600}h"
        elif duration.seconds >= 3600:
            return f"{duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m"
        elif duration.seconds >= 60:
            return f"{duration.seconds // 60}m {duration.seconds % 60}s"
        else:
            return f"{duration.seconds}s"
    
    @staticmethod
    def format_relative_time(timestamp: datetime) -> str:
        """Format relative time (e.g., "2 hours ago")."""
        now = datetime.now()
        
        if timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=None)
        if now.tzinfo:
            now = now.replace(tzinfo=None)
        
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return f"{diff.seconds} second{'s' if diff.seconds != 1 else ''} ago"
    
    @staticmethod
    def truncate_string(text: str, max_length: int = 50, 
                        suffix: str = "...") -> str:
        """Truncate string to maximum length."""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def format_list(items: List[str], max_items: int = 3,
                     item_prefix: str = "• ") -> str:
        """Format list with truncation if too many items."""
        if len(items) <= max_items:
            return "\n".join(f"{item_prefix}{item}" for item in items)
        else:
            shown_items = items[:max_items]
            remaining = len(items) - max_items
            return "\n".join(f"{item_prefix}{item}" for item in shown_items) + f"\n{item_prefix}... and {remaining} more"
    
    @staticmethod
    def format_tags(tags: Dict[str, str], max_tags: int = 5) -> str:
        """Format tags dictionary."""
        if not tags:
            return "No tags"
        
        tag_items = [f"{k}: {v}" for k, v in list(tags.items())[:max_tags]]
        
        if len(tags) > max_tags:
            tag_items.append(f"... and {len(tags) - max_tags} more")
        
        return ", ".join(tag_items)
    
    @staticmethod
    def format_table_data(data: List[Dict[str, Any]], 
                           headers: List[str]) -> List[List[str]]:
        """Format data for table display."""
        formatted_data = []
        
        # Add headers
        formatted_data.append(headers)
        
        # Add rows
        for row in data:
            formatted_row = []
            for header in headers:
                value = row.get(header, "")
                
                # Format based on type
                if isinstance(value, (int, float)):
                    if isinstance(value, float) and value % 1 != 0:
                        formatted_value = f"{value:,.2f}"
                    else:
                        formatted_value = f"{value:,}"
                elif isinstance(value, bool):
                    formatted_value = "✓" if value else "✗"
                elif isinstance(value, datetime):
                    formatted_value = value.strftime("%Y-%m-%d %H:%M")
                elif isinstance(value, list):
                    formatted_value = f"[{len(value)} items]"
                elif isinstance(value, dict):
                    formatted_value = f"[{len(value)} keys]"
                else:
                    formatted_value = str(value)
                
                # Truncate if too long
                formatted_value = FormatUtils.truncate_string(formatted_value, 30)
                formatted_row.append(formatted_value)
            
            formatted_data.append(formatted_row)
        
        return formatted_data
    
    @staticmethod
    def format_error_message(error: Exception, 
                             include_traceback: bool = False) -> str:
        """Format error message for display."""
        error_msg = f"{type(error).__name__}: {str(error)}"
        
        if include_traceback:
            import traceback
            traceback_msg = traceback.format_exc()
            error_msg += f"\n\nTraceback:\n{traceback_msg}"
        
        return error_msg
    
    @staticmethod
    def format_progress_bar(current: int, total: int, width: int = 50) -> str:
        """Format progress bar."""
        if total == 0:
            return "[" + "=" * width + "]"
        
        filled = int(width * current / total)
        empty = width - filled
        
        bar = "[" + "=" * filled + " " * empty + "]"
        
        percentage = (current / total) * 100
        return f"{bar} {percentage:.1f}%"
    
    @staticmethod
    def format_status_badge(status: str, color_map: Optional[Dict[str, str]] = None) -> str:
        """Format status badge."""
        if color_map is None:
            color_map = {
                'active': '🟢',
                'inactive': '🔴',
                'pending': '🟡',
                'completed': '✅',
                'failed': '❌',
                'warning': '⚠️',
                'info': 'ℹ️',
                'success': '✅',
                'error': '❌'
            }
        
        icon = color_map.get(status.lower(), status)
        return f"{icon} {status.title()}"


class DateUtils:
    """Date and time utilities."""
    
    @staticmethod
    def get_date_range(period: str, end_date: Optional[datetime] = None) -> tuple[datetime, datetime]:
        """Get date range for a period."""
        if end_date is None:
            end_date = datetime.now()
        
        if period == "today":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "yesterday":
            start_date = (end_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1) - timedelta(microseconds=1)
        elif period == "this_week":
            start_date = end_date - timedelta(days=end_date.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "last_week":
            start_date = end_date - timedelta(days=end_date.weekday() + 7)
            end_date = start_date + timedelta(days=7) - timedelta(microseconds=1)
        elif period == "this_month":
            start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "last_month":
            start_date = (end_date.replace(day=1) - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=31) - timedelta(microseconds=1)
            # Adjust to last day of previous month
            while start_date.month == end_date.month:
                end_date -= timedelta(days=1)
            end_date = end_date + timedelta(days=1)
        elif period == "this_year":
            start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "last_year":
            start_date = end_date.replace(year=end_date.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date.replace(year=start_date.year + 1) - timedelta(microseconds=1)
        else:
            # Assume it's a number of days
            try:
                days = int(period)
                start_date = end_date - timedelta(days=days)
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                raise CloudBillingError(f"Invalid period: {period}")
        
        return start_date, end_date
    
    @staticmethod
    def parse_date_string(date_str: str) -> datetime:
        """Parse date string in various formats."""
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S.%f",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.replace('Z', '+00:00'), fmt)
            except ValueError:
                continue
        
        raise CloudBillingError(f"Unable to parse date string: {date_str}")
    
    @staticmethod
    def get_month_start_end(date: datetime) -> tuple[datetime, datetime]:
        """Get start and end of month for given date."""
        start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get last day of month
        if date.month == 12:
            end = date.replace(year=date.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
        else:
            end = date.replace(month=date.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
        
        return start, end
    
    @staticmethod
    def get_week_start_end(date: datetime) -> tuple[datetime, datetime]:
        """Get start and end of week for given date."""
        start = date - timedelta(days=date.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        end = start + timedelta(days=7) - timedelta(microseconds=1)
        
        return start, end
    
    @staticmethod
    def is_weekend(date: datetime) -> bool:
        """Check if date is weekend."""
        return date.weekday() >= 5
    
    @staticmethod
    def is_business_day(date: datetime) -> bool:
        """Check if date is a business day."""
        return not DateUtils.is_weekend(date)
    
    @staticmethod
    def get_business_days(start_date: datetime, end_date: datetime) -> int:
        """Get number of business days between two dates."""
        business_days = 0
        current = start_date
        
        while current <= end_date:
            if DateUtils.is_business_day(current):
                business_days += 1
            current += timedelta(days=1)
        
        return business_days
    
    @staticmethod
    def add_business_days(date: datetime, days: int) -> datetime:
        """Add business days to a date."""
        current = date
        added_days = 0
        
        while added_days < days:
            current += timedelta(days=1)
            if DateUtils.is_business_day(current):
                added_days += 1
        
        return current
    
    @staticmethod
    def get_quarter_start_end(date: datetime) -> tuple[datetime, datetime]:
        """Get start and end of quarter for given date."""
        quarter = (date.month - 1) // 3 + 1
        year = date.year
        
        if quarter == 1:
            start = datetime(year, 1, 1)
            end = datetime(year, 4, 1) - timedelta(microseconds=1)
        elif quarter == 2:
            start = datetime(year, 4, 1)
            end = datetime(year, 7, 1) - timedelta(microseconds=1)
        elif quarter == 3:
            start = datetime(year, 7, 1)
            end = datetime(year, 10, 1) - timedelta(microseconds=1)
        else:  # quarter == 4
            start = datetime(year, 10, 1)
            end = datetime(year + 1, 1, 1) - timedelta(microseconds=1)
        
        return start, end
    
    @staticmethod
    def get_fiscal_year_start_end(fy_start_month: int = 1, 
                                   fy_start_day: int = 1,
                                   current_date: Optional[datetime] = None) -> tuple[datetime, datetime]:
        """Get fiscal year start and end."""
        if current_date is None:
            current_date = datetime.now()
        
        year = current_date.year
        
        # If current date is before fiscal year start, use previous year
        fiscal_start = datetime(year, fy_start_month, fy_start_day)
        if current_date < fiscal_start:
            year -= 1
        
        fiscal_start = datetime(year, fy_start_month, fy_start_day)
        fiscal_end = fiscal_start.replace(year=year + 1) - timedelta(microseconds=1)
        
        return fiscal_start, fiscal_end


class DataUtils:
    """Data manipulation utilities."""
    
    @staticmethod
    def deep_merge_dict(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataUtils.deep_merge_dict(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(DataUtils.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    @staticmethod
    def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely get value from nested dictionary."""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    @staticmethod
    def safe_set(data: Dict[str, Any], key: str, value: Any) -> None:
        """Safely set value in nested dictionary."""
        keys = key.split('.')
        current = data
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    @staticmethod
    def convert_to_csv(data: List[Dict[str, Any]]) -> str:
        """Convert list of dictionaries to CSV string."""
        if not data:
            return ""
        
        headers = list(data[0].keys())
        csv_lines = [",".join(headers)]
        
        for row in data:
            values = []
            for header in headers:
                value = row.get(header, "")
                # Handle commas and quotes in values
                if isinstance(value, str) and (',' in value or '"' in value):
                    value = f'"{value.replace('"', '""')}"'
                values.append(str(value))
            csv_lines.append(",".join(values))
        
        return "\n".join(csv_lines)
    
    @staticmethod
    def convert_to_json(data: Any, indent: int = 2) -> str:
        """Convert data to JSON string."""
        return json.dumps(data, indent=indent, default=str)
    
    @staticmethod
    def calculate_percent_change(old_value: float, new_value: float) -> float:
        """Calculate percentage change."""
        if old_value == 0:
            return 0.0 if new_value == 0 else float('inf')
        
        return ((new_value - old_value) / old_value) * 100
    
    @staticmethod
    def calculate_average(values: List[float]) -> float:
        """Calculate average of list of values."""
        return sum(values) / len(values) if values else 0.0
    
    @staticmethod
    def calculate_median(values: List[float]) -> float:
        """Calculate median of list of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        else:
            return sorted_values[n//2]
    
    @staticmethod
    def calculate_std_dev(values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        
        mean = DataUtils.calculate_average(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    @staticmethod
    def round_to_significant(value: float, sig_figs: int = 3) -> float:
        """Round number to significant figures."""
        if value == 0:
            return 0.0
        
        magnitude = 10 ** (sig_figs - 1 - int(math.log10(abs(value))))
        return round(value / magnitude) * magnitude
    
    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safe division with default value."""
        return numerator / denominator if denominator != 0 else default
