"""
Cost trend analysis for cloud billing data.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from ..collectors.base import BillingData
from ..core.exceptions import AnalyzerError


@dataclass
class TrendAnalysis:
    """Result of trend analysis."""
    metric: str
    trend_direction: str  # "increasing", "decreasing", "stable", "volatile"
    trend_strength: float  # 0-1, higher is stronger
    change_rate: float  # change per day
    confidence: float  # 0-1
    period_start: datetime
    period_end: datetime
    data_points: int


@dataclass
class SeasonalPattern:
    """Seasonal pattern detected in cost data."""
    pattern_type: str  # "daily", "weekly", "monthly"
    peak_periods: List[str]
    low_periods: List[str]
    amplitude: float
    confidence: float


@dataclass
class TrendForecast:
    """Forecast based on trend analysis."""
    forecast_values: List[float]
    forecast_dates: List[datetime]
    confidence_interval: Tuple[float, float]
    method: str
    accuracy_score: float


class TrendAnalyzer:
    """Analyzes trends in cloud billing data over time."""
    
    def __init__(self, config: Any):
        self.config = config
        self.min_data_points = 7  # Minimum data points for trend analysis
    
    def analyze_trends(self, billing_data: List[BillingData], 
                      metrics: List[str] = None) -> Dict[str, TrendAnalysis]:
        """Analyze trends for various cost metrics."""
        if metrics is None:
            metrics = ["total_cost", "service_costs", "regional_costs"]
        
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for trend analysis")
            
            # Convert to DataFrame
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            df['date'] = df['start_time'].dt.date
            
            results = {}
            
            # Analyze total cost trend
            if "total_cost" in metrics:
                total_trend = self._analyze_total_cost_trend(df)
                results["total_cost"] = total_trend
            
            # Analyze service-level trends
            if "service_costs" in metrics:
                service_trends = self._analyze_service_trends(df)
                results.update(service_trends)
            
            # Analyze regional trends
            if "regional_costs" in metrics:
                regional_trends = self._analyze_regional_trends(df)
                results.update(regional_trends)
            
            return results
            
        except Exception as e:
            raise AnalyzerError(f"Failed to analyze trends: {e}")
    
    def detect_seasonal_patterns(self, billing_data: List[BillingData]) -> List[SeasonalPattern]:
        """Detect seasonal patterns in cost data."""
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for seasonal analysis")
            
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            df['date'] = df['start_time'].dt.date
            df['hour'] = df['start_time'].dt.hour
            df['day_of_week'] = df['start_time'].dt.dayofweek
            df['day_of_month'] = df['start_time'].dt.day
            
            patterns = []
            
            # Daily patterns (hourly)
            if len(df) >= 24 * 7:  # Need at least a week of hourly data
                daily_pattern = self._detect_daily_pattern(df)
                if daily_pattern:
                    patterns.append(daily_pattern)
            
            # Weekly patterns
            if len(df) >= 7 * 4:  # Need at least 4 weeks of data
                weekly_pattern = self._detect_weekly_pattern(df)
                if weekly_pattern:
                    patterns.append(weekly_pattern)
            
            # Monthly patterns
            if len(df) >= 30 * 3:  # Need at least 3 months of data
                monthly_pattern = self._detect_monthly_pattern(df)
                if monthly_pattern:
                    patterns.append(monthly_pattern)
            
            return patterns
            
        except Exception as e:
            raise AnalyzerError(f"Failed to detect seasonal patterns: {e}")
    
    def forecast_trends(self, billing_data: List[BillingData], 
                       forecast_days: int = 30) -> TrendForecast:
        """Forecast future costs based on trend analysis."""
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for forecasting")
            
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            df['date'] = df['start_time'].dt.date
            
            # Group by date for daily totals
            daily_costs = df.groupby('date')['cost'].sum().reset_index()
            daily_costs['date'] = pd.to_datetime(daily_costs['date'])
            
            if len(daily_costs) < self.min_data_points:
                raise AnalyzerError(f"Insufficient data for forecasting (need at least {self.min_data_points} days)")
            
            # Try different forecasting methods
            forecasts = []
            
            # Linear regression
            linear_forecast = self._linear_regression_forecast(daily_costs, forecast_days)
            if linear_forecast:
                forecasts.append(linear_forecast)
            
            # Moving average
            ma_forecast = self._moving_average_forecast(daily_costs, forecast_days)
            if ma_forecast:
                forecasts.append(ma_forecast)
            
            # Exponential smoothing
            es_forecast = self._exponential_smoothing_forecast(daily_costs, forecast_days)
            if es_forecast:
                forecasts.append(es_forecast)
            
            # Select best forecast based on accuracy score
            if forecasts:
                best_forecast = max(forecasts, key=lambda x: x.accuracy_score)
                return best_forecast
            else:
                raise AnalyzerError("All forecasting methods failed")
            
        except Exception as e:
            raise AnalyzerError(f"Failed to forecast trends: {e}")
    
    def compare_periods(self, billing_data: List[BillingData], 
                       period1: Tuple[datetime, datetime],
                       period2: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Compare costs between two time periods."""
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for period comparison")
            
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            
            # Filter data for each period
            period1_data = df[(df['start_time'] >= period1[0]) & (df['start_time'] <= period1[1])]
            period2_data = df[(df['start_time'] >= period2[0]) & (df['start_time'] <= period2[1])]
            
            if period1_data.empty or period2_data.empty:
                raise AnalyzerError("No data found for specified periods")
            
            # Calculate metrics for each period
            period1_total = period1_data['cost'].sum()
            period2_total = period2_data['cost'].sum()
            
            period1_services = period1_data.groupby('service')['cost'].sum().to_dict()
            period2_services = period2_data.groupby('service')['cost'].sum().to_dict()
            
            period1_regions = period1_data.groupby('region')['cost'].sum().to_dict()
            period2_regions = period2_data.groupby('region')['cost'].sum().to_dict()
            
            # Calculate changes
            total_change = period2_total - period1_total
            total_change_pct = (total_change / period1_total * 100) if period1_total > 0 else 0
            
            # Service changes
            service_changes = {}
            all_services = set(period1_services.keys()) | set(period2_services.keys())
            for service in all_services:
                p1_cost = period1_services.get(service, 0)
                p2_cost = period2_services.get(service, 0)
                change = p2_cost - p1_cost
                change_pct = (change / p1_cost * 100) if p1_cost > 0 else 0
                service_changes[service] = {
                    'period1_cost': p1_cost,
                    'period2_cost': p2_cost,
                    'change': change,
                    'change_percentage': change_pct
                }
            
            # Regional changes
            region_changes = {}
            all_regions = set(period1_regions.keys()) | set(period2_regions.keys())
            for region in all_regions:
                p1_cost = period1_regions.get(region, 0)
                p2_cost = period2_regions.get(region, 0)
                change = p2_cost - p1_cost
                change_pct = (change / p1_cost * 100) if p1_cost > 0 else 0
                region_changes[region] = {
                    'period1_cost': p1_cost,
                    'period2_cost': p2_cost,
                    'change': change,
                    'change_percentage': change_pct
                }
            
            return {
                'period1': {
                    'start': period1[0],
                    'end': period1[1],
                    'total_cost': period1_total,
                    'duration_days': (period1[1] - period1[0]).days
                },
                'period2': {
                    'start': period2[0],
                    'end': period2[1],
                    'total_cost': period2_total,
                    'duration_days': (period2[1] - period2[0]).days
                },
                'comparison': {
                    'total_change': total_change,
                    'total_change_percentage': total_change_pct,
                    'service_changes': service_changes,
                    'region_changes': region_changes
                }
            }
            
        except Exception as e:
            raise AnalyzerError(f"Failed to compare periods: {e}")
    
    def _analyze_total_cost_trend(self, df: pd.DataFrame) -> TrendAnalysis:
        """Analyze total cost trend."""
        # Group by date
        daily_costs = df.groupby('date')['cost'].sum().reset_index()
        daily_costs['date'] = pd.to_datetime(daily_costs['date'])
        
        if len(daily_costs) < self.min_data_points:
            return TrendAnalysis(
                metric="total_cost",
                trend_direction="insufficient_data",
                trend_strength=0.0,
                change_rate=0.0,
                confidence=0.0,
                period_start=daily_costs['date'].min(),
                period_end=daily_costs['date'].max(),
                data_points=len(daily_costs)
            )
        
        # Calculate trend using linear regression
        X = np.arange(len(daily_costs))
        y = daily_costs['cost'].values
        
        coeffs = np.polyfit(X, y, 1)
        slope = coeffs[0]
        
        # Calculate trend strength (R-squared)
        y_pred = np.polyval(coeffs, X)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Determine trend direction
        if abs(slope) < 0.01:  # Very small slope
            trend_direction = "stable"
        elif slope > 0:
            trend_direction = "increasing"
        else:
            trend_direction = "decreasing"
        
        # Calculate volatility
        volatility = np.std(y) / np.mean(y) if np.mean(y) > 0 else 0
        if volatility > 0.5:
            trend_direction = "volatile"
        
        return TrendAnalysis(
            metric="total_cost",
            trend_direction=trend_direction,
            trend_strength=r_squared,
            change_rate=slope,
            confidence=min(1.0, r_squared * (len(daily_costs) / 30)),  # Adjust confidence by data points
            period_start=daily_costs['date'].min(),
            period_end=daily_costs['date'].max(),
            data_points=len(daily_costs)
        )
    
    def _analyze_service_trends(self, df: pd.DataFrame) -> Dict[str, TrendAnalysis]:
        """Analyze trends for each service."""
        trends = {}
        
        for service in df['service'].unique():
            service_data = df[df['service'] == service]
            
            # Group by date
            daily_costs = service_data.groupby('date')['cost'].sum().reset_index()
            daily_costs['date'] = pd.to_datetime(daily_costs['date'])
            
            if len(daily_costs) < self.min_data_points:
                continue
            
            # Linear regression
            X = np.arange(len(daily_costs))
            y = daily_costs['cost'].values
            
            coeffs = np.polyfit(X, y, 1)
            slope = coeffs[0]
            
            # R-squared
            y_pred = np.polyval(coeffs, X)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Trend direction
            if abs(slope) < 0.01:
                trend_direction = "stable"
            elif slope > 0:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"
            
            trends[service] = TrendAnalysis(
                metric=f"service_{service}",
                trend_direction=trend_direction,
                trend_strength=r_squared,
                change_rate=slope,
                confidence=min(1.0, r_squared * (len(daily_costs) / 30)),
                period_start=daily_costs['date'].min(),
                period_end=daily_costs['date'].max(),
                data_points=len(daily_costs)
            )
        
        return trends
    
    def _analyze_regional_trends(self, df: pd.DataFrame) -> Dict[str, TrendAnalysis]:
        """Analyze trends for each region."""
        trends = {}
        
        for region in df['region'].unique():
            if region == 'Unknown':
                continue
                
            region_data = df[df['region'] == region]
            
            # Group by date
            daily_costs = region_data.groupby('date')['cost'].sum().reset_index()
            daily_costs['date'] = pd.to_datetime(daily_costs['date'])
            
            if len(daily_costs) < self.min_data_points:
                continue
            
            # Linear regression
            X = np.arange(len(daily_costs))
            y = daily_costs['cost'].values
            
            coeffs = np.polyfit(X, y, 1)
            slope = coeffs[0]
            
            # R-squared
            y_pred = np.polyval(coeffs, X)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Trend direction
            if abs(slope) < 0.01:
                trend_direction = "stable"
            elif slope > 0:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"
            
            trends[region] = TrendAnalysis(
                metric=f"region_{region}",
                trend_direction=trend_direction,
                trend_strength=r_squared,
                change_rate=slope,
                confidence=min(1.0, r_squared * (len(daily_costs) / 30)),
                period_start=daily_costs['date'].min(),
                period_end=daily_costs['date'].max(),
                data_points=len(daily_costs)
            )
        
        return trends
    
    def _detect_daily_pattern(self, df: pd.DataFrame) -> Optional[SeasonalPattern]:
        """Detect daily (hourly) patterns."""
        try:
            hourly_costs = df.groupby('hour')['cost'].mean()
            
            if len(hourly_costs) < 24:
                return None
            
            # Find peak and low hours
            peak_hours = hourly_costs.nlargest(3).index.tolist()
            low_hours = hourly_costs.nsmallest(3).index.tolist()
            
            # Calculate amplitude
            amplitude = (hourly_costs.max() - hourly_costs.min()) / hourly_costs.mean()
            
            # Calculate confidence based on pattern consistency
            confidence = min(1.0, amplitude / 2.0)
            
            return SeasonalPattern(
                pattern_type="daily",
                peak_periods=[f"{h:02d}:00" for h in peak_hours],
                low_periods=[f"{h:02d}:00" for h in low_hours],
                amplitude=amplitude,
                confidence=confidence
            )
            
        except Exception:
            return None
    
    def _detect_weekly_pattern(self, df: pd.DataFrame) -> Optional[SeasonalPattern]:
        """Detect weekly patterns."""
        try:
            daily_costs = df.groupby('day_of_week')['cost'].mean()
            
            if len(daily_costs) < 7:
                return None
            
            # Find peak and low days
            peak_days = daily_costs.nlargest(2).index.tolist()
            low_days = daily_costs.nsmallest(2).index.tolist()
            
            day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            
            # Calculate amplitude
            amplitude = (daily_costs.max() - daily_costs.min()) / daily_costs.mean()
            
            # Calculate confidence
            confidence = min(1.0, amplitude / 2.0)
            
            return SeasonalPattern(
                pattern_type="weekly",
                peak_periods=[day_names[d] for d in peak_days],
                low_periods=[day_names[d] for d in low_days],
                amplitude=amplitude,
                confidence=confidence
            )
            
        except Exception:
            return None
    
    def _detect_monthly_pattern(self, df: pd.DataFrame) -> Optional[SeasonalPattern]:
        """Detect monthly patterns."""
        try:
            daily_costs = df.groupby('day_of_month')['cost'].mean()
            
            if len(daily_costs) < 28:
                return None
            
            # Find peak and low days
            peak_days = daily_costs.nlargest(3).index.tolist()
            low_days = daily_costs.nsmallest(3).index.tolist()
            
            # Calculate amplitude
            amplitude = (daily_costs.max() - daily_costs.min()) / daily_costs.mean()
            
            # Calculate confidence
            confidence = min(1.0, amplitude / 2.0)
            
            return SeasonalPattern(
                pattern_type="monthly",
                peak_periods=[f"Day {d}" for d in peak_days],
                low_periods=[f"Day {d}" for d in low_days],
                amplitude=amplitude,
                confidence=confidence
            )
            
        except Exception:
            return None
    
    def _linear_regression_forecast(self, daily_costs: pd.DataFrame, 
                                   forecast_days: int) -> Optional[TrendForecast]:
        """Linear regression forecasting."""
        try:
            X = np.arange(len(daily_costs))
            y = daily_costs['cost'].values
            
            # Fit linear regression
            coeffs = np.polyfit(X, y, 1)
            
            # Generate forecast
            last_date = daily_costs['date'].max()
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(forecast_days)]
            forecast_X = np.arange(len(daily_costs), len(daily_costs) + forecast_days)
            forecast_values = np.polyval(coeffs, forecast_X)
            
            # Calculate confidence interval
            y_pred = np.polyval(coeffs, X)
            residuals = y - y_pred
            std_error = np.std(residuals)
            
            # Calculate accuracy (R-squared)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            return TrendForecast(
                forecast_values=forecast_values.tolist(),
                forecast_dates=forecast_dates,
                confidence_interval=(std_error, std_error),
                method="linear_regression",
                accuracy_score=max(0, r_squared)
            )
            
        except Exception:
            return None
    
    def _moving_average_forecast(self, daily_costs: pd.DataFrame, 
                                forecast_days: int, window: int = 7) -> Optional[TrendForecast]:
        """Moving average forecasting."""
        try:
            if len(daily_costs) < window * 2:
                return None
            
            # Calculate moving average
            ma_values = daily_costs['cost'].rolling(window=window).mean().dropna()
            
            # Use last MA value for forecast
            last_ma = ma_values.iloc[-1]
            forecast_values = [last_ma] * forecast_days
            
            last_date = daily_costs['date'].max()
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(forecast_days)]
            
            # Calculate confidence interval
            std_error = daily_costs['cost'].rolling(window=window).std().dropna().iloc[-1]
            
            # Simple accuracy calculation based on recent fit
            recent_actual = daily_costs['cost'].tail(window).values
            recent_ma = ma_values.tail(window).values
            mae = np.mean(np.abs(recent_actual - recent_ma))
            accuracy = max(0, 1 - (mae / np.mean(recent_actual))) if np.mean(recent_actual) > 0 else 0
            
            return TrendForecast(
                forecast_values=forecast_values,
                forecast_dates=forecast_dates,
                confidence_interval=(std_error, std_error),
                method="moving_average",
                accuracy_score=accuracy
            )
            
        except Exception:
            return None
    
    def _exponential_smoothing_forecast(self, daily_costs: pd.DataFrame, 
                                      forecast_days: int, alpha: float = 0.3) -> Optional[TrendForecast]:
        """Exponential smoothing forecasting."""
        try:
            values = daily_costs['cost'].values
            
            # Simple exponential smoothing
            smoothed = [values[0]]
            for i in range(1, len(values)):
                smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[-1])
            
            # Forecast using last smoothed value
            last_smoothed = smoothed[-1]
            forecast_values = [last_smoothed] * forecast_days
            
            last_date = daily_costs['date'].max()
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(forecast_days)]
            
            # Calculate confidence interval
            errors = [abs(values[i] - smoothed[i]) for i in range(len(values))]
            std_error = np.std(errors)
            
            # Calculate accuracy
            mae = np.mean(errors)
            accuracy = max(0, 1 - (mae / np.mean(values))) if np.mean(values) > 0 else 0
            
            return TrendForecast(
                forecast_values=forecast_values,
                forecast_dates=forecast_dates,
                confidence_interval=(std_error, std_error),
                method="exponential_smoothing",
                accuracy_score=accuracy
            )
            
        except Exception:
            return None
    
    def _billing_data_to_dict(self, data: BillingData) -> Dict[str, Any]:
        """Convert BillingData to dictionary."""
        return {
            'provider': data.provider,
            'account_id': data.account_id,
            'service': data.service,
            'region': data.region,
            'resource_id': data.resource_id,
            'resource_name': data.resource_name,
            'usage_type': data.usage_type,
            'usage_amount': data.usage_amount,
            'usage_unit': data.usage_unit,
            'cost': data.cost,
            'currency': data.currency,
            'start_time': data.start_time,
            'end_time': data.end_time,
            'tags': data.tags,
            'environment': data.environment,
            'cost_center': data.cost_center
        }
