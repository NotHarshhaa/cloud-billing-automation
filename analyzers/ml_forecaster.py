"""
Machine learning-based budget forecasting.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from enum import Enum
import logging

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ..core.config import Config
from ..core.exceptions import AnalyzerError
from ..collectors.base import BillingData
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class ForecastModel(Enum):
    """Available forecasting models."""
    LINEAR = "linear"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"


@dataclass
class ForecastResult:
    """Budget forecast result."""
    forecast_values: List[float]
    forecast_dates: List[datetime]
    model_used: str
    accuracy_metrics: Dict[str, float]
    confidence_intervals: Optional[List[Tuple[float, float]]] = None
    feature_importance: Optional[Dict[str, float]] = None
    training_data_points: int = 0


class BudgetForecaster:
    """Machine learning-based budget forecasting."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        
    def forecast_budget(self, billing_data: List[BillingData], 
                       forecast_days: int = 30,
                       model: ForecastModel = ForecastModel.LINEAR) -> ForecastResult:
        """Generate budget forecast using machine learning models."""
        try:
            self.logger.info(f"Starting budget forecast for {forecast_days} days using {model.value}")
            
            # Prepare data
            df = self._prepare_forecast_data(billing_data)
            if df.empty or len(df) < 7:
                raise AnalyzerError("Insufficient data for forecasting (minimum 7 days required)")
            
            # Generate forecast based on selected model
            if model == ForecastModel.LINEAR:
                result = self._linear_regression_forecast(df, forecast_days)
            elif model == ForecastModel.RANDOM_FOREST:
                result = self._random_forest_forecast(df, forecast_days)
            elif model == ForecastModel.GRADIENT_BOOSTING:
                result = self._gradient_boosting_forecast(df, forecast_days)
            elif model == ForecastModel.MOVING_AVERAGE:
                result = self._moving_average_forecast(df, forecast_days)
            elif model == ForecastModel.EXPONENTIAL_SMOOTHING:
                result = self._exponential_smoothing_forecast(df, forecast_days)
            else:
                raise AnalyzerError(f"Unsupported forecast model: {model}")
            
            self.logger.info(f"Forecast completed using {model.value} model")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in budget forecasting: {e}", exc_info=True)
            raise AnalyzerError(f"Failed to generate budget forecast: {e}")
    
    def _prepare_forecast_data(self, billing_data: List[BillingData]) -> pd.DataFrame:
        """Prepare billing data for forecasting."""
        # Convert to DataFrame
        data = []
        for billing in billing_data:
            data.append({
                'date': billing.start_time.date(),
                'cost': billing.cost,
                'service': billing.service,
                'region': billing.region,
                'environment': billing.environment or 'unknown'
            })
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Aggregate by date
        daily_costs = df.groupby('date')['cost'].sum().reset_index()
        daily_costs['date'] = pd.to_datetime(daily_costs['date'])
        daily_costs = daily_costs.sort_values('date')
        
        # Add features
        daily_costs = self._add_forecast_features(daily_costs)
        
        return daily_costs
    
    def _add_forecast_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add features for machine learning models."""
        df = df.copy()
        
        # Time-based features
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['week_of_year'] = df['date'].dt.isocalendar().week
        
        # Lag features
        for lag in [1, 7, 14, 30]:
            df[f'cost_lag_{lag}'] = df['cost'].shift(lag)
        
        # Rolling statistics
        for window in [7, 14, 30]:
            df[f'cost_rolling_mean_{window}'] = df['cost'].rolling(window=window).mean()
            df[f'cost_rolling_std_{window}'] = df['cost'].rolling(window=window).std()
        
        # Trend features
        df['cost_trend_7'] = df['cost'].rolling(window=7).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0)
        df['cost_trend_30'] = df['cost'].rolling(window=30).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0)
        
        # Day of week averages
        dow_avg = df.groupby('day_of_week')['cost'].mean()
        df['dow_avg'] = df['day_of_week'].map(dow_avg)
        
        return df
    
    def _linear_regression_forecast(self, df: pd.DataFrame, forecast_days: int) -> ForecastResult:
        """Linear regression forecast."""
        if not SKLEARN_AVAILABLE:
            return self._simple_linear_forecast(df, forecast_days)
        
        # Prepare features
        feature_cols = [col for col in df.columns if col not in ['date', 'cost']]
        df_clean = df.dropna()
        
        if len(df_clean) < 10:
            return self._simple_linear_forecast(df, forecast_days)
        
        X = df_clean[feature_cols].values
        y = df_clean['cost'].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        model = LinearRegression()
        model.fit(X_scaled, y)
        
        # Generate future dates
        last_date = df['date'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
        
        # Create features for future dates
        future_df = pd.DataFrame({'date': future_dates})
        future_df = self._add_forecast_features(future_df)
        
        # Fill missing lag features with last known values
        for col in feature_cols:
            if col not in future_df.columns:
                if 'lag' in col:
                    future_df[col] = df['cost'].iloc[-1]  # Use last known cost
                elif 'rolling' in col:
                    future_df[col] = df[col].iloc[-1] if col in df.columns else df['cost'].mean()
                else:
                    future_df[col] = df[col].iloc[-1] if col in df.columns else 0
        
        # Predict
        X_future = future_df[feature_cols].values
        X_future_scaled = self.scaler.transform(X_future)
        forecast_values = model.predict(X_future_scaled)
        
        # Calculate accuracy metrics
        y_pred = model.predict(X_scaled)
        mae = mean_absolute_error(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        
        return ForecastResult(
            forecast_values=forecast_values.tolist(),
            forecast_dates=future_dates,
            model_used="Linear Regression",
            accuracy_metrics={
                'mae': mae,
                'mse': mse,
                'rmse': np.sqrt(mse),
                'mape': np.mean(np.abs((y - y_pred) / y)) * 100
            },
            feature_importance=dict(zip(feature_cols, np.abs(model.coef_))),
            training_data_points=len(df_clean)
        )
    
    def _random_forest_forecast(self, df: pd.DataFrame, forecast_days: int) -> ForecastResult:
        """Random Forest forecast."""
        if not SKLEARN_AVAILABLE:
            return self._simple_linear_forecast(df, forecast_days)
        
        # Prepare features
        feature_cols = [col for col in df.columns if col not in ['date', 'cost']]
        df_clean = df.dropna()
        
        if len(df_clean) < 10:
            return self._simple_linear_forecast(df, forecast_days)
        
        X = df_clean[feature_cols].values
        y = df_clean['cost'].values
        
        # Train model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Generate future dates and features (same as linear regression)
        last_date = df['date'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
        
        future_df = pd.DataFrame({'date': future_dates})
        future_df = self._add_forecast_features(future_df)
        
        # Fill missing features
        for col in feature_cols:
            if col not in future_df.columns:
                if 'lag' in col:
                    future_df[col] = df['cost'].iloc[-1]
                elif 'rolling' in col:
                    future_df[col] = df[col].iloc[-1] if col in df.columns else df['cost'].mean()
                else:
                    future_df[col] = df[col].iloc[-1] if col in df.columns else 0
        
        # Predict
        X_future = future_df[feature_cols].values
        forecast_values = model.predict(X_future)
        
        # Calculate accuracy metrics
        y_pred = model.predict(X)
        mae = mean_absolute_error(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        
        return ForecastResult(
            forecast_values=forecast_values.tolist(),
            forecast_dates=future_dates,
            model_used="Random Forest",
            accuracy_metrics={
                'mae': mae,
                'mse': mse,
                'rmse': np.sqrt(mse),
                'mape': np.mean(np.abs((y - y_pred) / y)) * 100
            },
            feature_importance=dict(zip(feature_cols, model.feature_importances_)),
            training_data_points=len(df_clean)
        )
    
    def _gradient_boosting_forecast(self, df: pd.DataFrame, forecast_days: int) -> ForecastResult:
        """Gradient Boosting forecast."""
        if not SKLEARN_AVAILABLE:
            return self._simple_linear_forecast(df, forecast_days)
        
        # Similar to Random Forest but with Gradient Boosting
        feature_cols = [col for col in df.columns if col not in ['date', 'cost']]
        df_clean = df.dropna()
        
        if len(df_clean) < 10:
            return self._simple_linear_forecast(df, forecast_days)
        
        X = df_clean[feature_cols].values
        y = df_clean['cost'].values
        
        model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Generate forecast (same process as other models)
        last_date = df['date'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
        
        future_df = pd.DataFrame({'date': future_dates})
        future_df = self._add_forecast_features(future_df)
        
        for col in feature_cols:
            if col not in future_df.columns:
                if 'lag' in col:
                    future_df[col] = df['cost'].iloc[-1]
                elif 'rolling' in col:
                    future_df[col] = df[col].iloc[-1] if col in df.columns else df['cost'].mean()
                else:
                    future_df[col] = df[col].iloc[-1] if col in df.columns else 0
        
        X_future = future_df[feature_cols].values
        forecast_values = model.predict(X_future)
        
        y_pred = model.predict(X)
        mae = mean_absolute_error(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        
        return ForecastResult(
            forecast_values=forecast_values.tolist(),
            forecast_dates=future_dates,
            model_used="Gradient Boosting",
            accuracy_metrics={
                'mae': mae,
                'mse': mse,
                'rmse': np.sqrt(mse),
                'mape': np.mean(np.abs((y - y_pred) / y)) * 100
            },
            feature_importance=dict(zip(feature_cols, model.feature_importances_)),
            training_data_points=len(df_clean)
        )
    
    def _moving_average_forecast(self, df: pd.DataFrame, forecast_days: int) -> ForecastResult:
        """Moving average forecast."""
        # Use 30-day moving average
        window = min(30, len(df) // 2)
        if window < 3:
            window = len(df)
        
        recent_costs = df['cost'].tail(window).values
        forecast_values = []
        
        for i in range(forecast_days):
            # Simple moving average prediction
            next_value = np.mean(recent_costs[-window:])
            forecast_values.append(next_value)
            recent_costs = np.append(recent_costs, next_value)
        
        last_date = df['date'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
        
        # Calculate accuracy on training data
        train_predictions = []
        for i in range(window, len(df)):
            train_predictions.append(np.mean(df['cost'].iloc[i-window:i].values))
        
        if train_predictions:
            actual = df['cost'].iloc[window:].values
            mae = mean_absolute_error(actual, train_predictions)
            mse = mean_squared_error(actual, train_predictions)
        else:
            mae = mse = 0
        
        return ForecastResult(
            forecast_values=forecast_values,
            forecast_dates=future_dates,
            model_used="Moving Average",
            accuracy_metrics={
                'mae': mae,
                'mse': mse,
                'rmse': np.sqrt(mse),
                'mape': 0
            },
            training_data_points=len(df)
        )
    
    def _exponential_smoothing_forecast(self, df: pd.DataFrame, forecast_days: int) -> ForecastResult:
        """Exponential smoothing forecast."""
        # Simple exponential smoothing
        alpha = 0.3  # Smoothing factor
        
        costs = df['cost'].values
        forecast_values = []
        
        # Initialize with last value
        last_smoothed = costs[-1]
        
        for i in range(forecast_days):
            forecast_values.append(last_smoothed)
            # Update smoothed value (would normally use actual values, but we're forecasting)
            last_smoothed = alpha * last_smoothed + (1 - alpha) * last_smoothed
        
        last_date = df['date'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
        
        # Calculate accuracy on training data
        smoothed = [costs[0]]
        for i in range(1, len(costs)):
            smoothed.append(alpha * costs[i-1] + (1 - alpha) * smoothed[-1])
        
        if len(smoothed) > 1:
            actual = costs[1:]
            pred = smoothed[:-1]
            mae = mean_absolute_error(actual, pred)
            mse = mean_squared_error(actual, pred)
        else:
            mae = mse = 0
        
        return ForecastResult(
            forecast_values=forecast_values,
            forecast_dates=future_dates,
            model_used="Exponential Smoothing",
            accuracy_metrics={
                'mae': mae,
                'mse': mse,
                'rmse': np.sqrt(mse),
                'mape': 0
            },
            training_data_points=len(df)
        )
    
    def _simple_linear_forecast(self, df: pd.DataFrame, forecast_days: int) -> ForecastResult:
        """Simple linear trend forecast (fallback when sklearn not available)."""
        # Simple linear trend
        x = np.arange(len(df))
        y = df['cost'].values
        
        # Fit linear trend
        coeffs = np.polyfit(x, y, 1)
        trend = coeffs[0]
        intercept = coeffs[1]
        
        # Generate forecast
        future_x = np.arange(len(df), len(df) + forecast_days)
        forecast_values = trend * future_x + intercept
        
        last_date = df['date'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
        
        # Calculate accuracy
        y_pred = trend * x + intercept
        mae = mean_absolute_error(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        
        return ForecastResult(
            forecast_values=forecast_values.tolist(),
            forecast_dates=future_dates,
            model_used="Simple Linear Trend",
            accuracy_metrics={
                'mae': mae,
                'mse': mse,
                'rmse': np.sqrt(mse),
                'mape': np.mean(np.abs((y - y_pred) / y)) * 100
            },
            training_data_points=len(df)
        )
    
    def compare_models(self, billing_data: List[BillingData], forecast_days: int = 30) -> Dict[str, ForecastResult]:
        """Compare multiple forecasting models."""
        models = [
            ForecastModel.LINEAR,
            ForecastModel.MOVING_AVERAGE,
            ForecastModel.EXPONENTIAL_SMOOTHING
        ]
        
        if SKLEARN_AVAILABLE:
            models.extend([
                ForecastModel.RANDOM_FOREST,
                ForecastModel.GRADIENT_BOOSTING
            ])
        
        results = {}
        for model in models:
            try:
                results[model.value] = self.forecast_budget(billing_data, forecast_days, model)
            except Exception as e:
                self.logger.warning(f"Model {model.value} failed: {e}")
        
        return results
