"""
Cost forecasting for cloud billing data.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from ..collectors.base import BillingData
from ..core.exceptions import AnalyzerError


@dataclass
class ForecastResult:
    """Result of cost forecasting."""
    forecast_values: List[float]
    forecast_dates: List[datetime]
    confidence_intervals: List[Tuple[float, float]]  # (lower, upper) bounds
    model_used: str
    accuracy_metrics: Dict[str, float]
    feature_importance: Optional[Dict[str, float]]
    assumptions: List[str]


@dataclass
class BudgetForecast:
    """Budget forecast with risk assessment."""
    current_budget: float
    forecasted_spend: float
    budget_variance: float
    risk_level: str  # "low", "medium", "high", "critical"
    overrun_probability: float
    recommended_budget: float
    cost_saving_opportunities: List[str]


class CostForecaster:
    """Advanced cost forecasting using machine learning models."""
    
    def __init__(self, config: Any):
        self.config = config
        self.models = {
            'linear': LinearRegression(),
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42)
        }
        self.min_training_days = 30
    
    def forecast_costs(self, billing_data: List[BillingData], 
                      forecast_days: int = 30,
                      model: str = 'auto') -> ForecastResult:
        """Forecast future costs using machine learning models."""
        try:
            if not billing_data:
                raise AnalyzerError("No billing data provided for forecasting")
            
            df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
            
            # Prepare data for modeling
            prepared_data = self._prepare_forecast_data(df)
            
            if len(prepared_data) < self.min_training_days:
                raise AnalyzerError(f"Insufficient data for forecasting (need at least {self.min_training_days} days)")
            
            # Select model
            if model == 'auto':
                model = self._select_best_model(prepared_data)
            
            # Train model and generate forecast
            forecast_result = self._train_and_forecast(prepared_data, forecast_days, model)
            
            return forecast_result
            
        except Exception as e:
            raise AnalyzerError(f"Failed to forecast costs: {e}")
    
    def forecast_budget_impact(self, billing_data: List[BillingData], 
                             monthly_budget: float,
                             forecast_days: int = 30) -> BudgetForecast:
        """Forecast budget impact and risk assessment."""
        try:
            # Get cost forecast
            cost_forecast = self.forecast_costs(billing_data, forecast_days)
            
            # Calculate forecasted spend for the period
            forecasted_spend = sum(cost_forecast.forecast_values)
            
            # Calculate budget variance
            budget_variance = forecasted_spend - monthly_budget
            
            # Assess risk level
            risk_level = self._assess_budget_risk(budget_variance, monthly_budget)
            
            # Calculate overrun probability
            overrun_probability = self._calculate_overrun_probability(cost_forecast, monthly_budget)
            
            # Recommend budget adjustment
            recommended_budget = self._recommend_budget_adjustment(forecasted_spend, monthly_budget)
            
            # Identify cost saving opportunities
            cost_saving_opportunities = self._identify_cost_saving_opportunities(billing_data)
            
            return BudgetForecast(
                current_budget=monthly_budget,
                forecasted_spend=forecasted_spend,
                budget_variance=budget_variance,
                risk_level=risk_level,
                overrun_probability=overrun_probability,
                recommended_budget=recommended_budget,
                cost_saving_opportunities=cost_saving_opportunities
            )
            
        except Exception as e:
            raise AnalyzerError(f"Failed to forecast budget impact: {e}")
    
    def forecast_scenario_analysis(self, billing_data: List[BillingData],
                                 scenarios: Dict[str, Dict[str, float]]) -> Dict[str, ForecastResult]:
        """Perform scenario-based forecasting."""
        try:
            scenario_results = {}
            
            for scenario_name, scenario_params in scenarios.items():
                # Apply scenario adjustments to data
                adjusted_data = self._apply_scenario_adjustments(billing_data, scenario_params)
                
                # Generate forecast for adjusted data
                forecast_result = self.forecast_costs(adjusted_data, forecast_days=30)
                
                scenario_results[scenario_name] = forecast_result
            
            return scenario_results
            
        except Exception as e:
            raise AnalyzerError(f"Failed to perform scenario analysis: {e}")
    
    def forecast_resource_optimization(self, billing_data: List[BillingData],
                                     optimization_suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Forecast impact of resource optimization suggestions."""
        try:
            # Get baseline forecast
            baseline_forecast = self.forecast_costs(billing_data, forecast_days=30)
            
            # Apply optimization suggestions
            optimization_impact = {}
            
            for suggestion in optimization_suggestions:
                suggestion_name = suggestion.get('name', 'unnamed')
                expected_savings = suggestion.get('expected_savings', 0)
                implementation_time = suggestion.get('implementation_time', 0)
                
                # Calculate cumulative savings over forecast period
                cumulative_savings = 0
                adjusted_forecast = baseline_forecast.forecast_values.copy()
                
                for i in range(len(adjusted_forecast)):
                    if i >= implementation_time:
                        daily_savings = expected_savings / 30  # Convert monthly to daily
                        adjusted_forecast[i] -= daily_savings
                        cumulative_savings += daily_savings
                
                optimization_impact[suggestion_name] = {
                    'original_forecast': baseline_forecast.forecast_values,
                    'optimized_forecast': adjusted_forecast,
                    'total_savings': cumulative_savings,
                    'savings_percentage': (cumulative_savings / sum(baseline_forecast.forecast_values) * 100) if sum(baseline_forecast.forecast_values) > 0 else 0
                }
            
            return optimization_impact
            
        except Exception as e:
            raise AnalyzerError(f"Failed to forecast resource optimization: {e}")
    
    def _prepare_forecast_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for forecasting models."""
        try:
            # Group by date for daily totals
            daily_data = df.groupby(df['start_time'].dt.date).agg({
                'cost': 'sum',
                'usage_amount': 'sum'
            }).reset_index()
            
            daily_data.columns = ['date', 'total_cost', 'total_usage']
            daily_data['date'] = pd.to_datetime(daily_data['date'])
            
            # Add time-based features
            daily_data['day_of_week'] = daily_data['date'].dt.dayofweek
            daily_data['day_of_month'] = daily_data['date'].dt.day
            daily_data['month'] = daily_data['date'].dt.month
            daily_data['quarter'] = daily_data['date'].dt.quarter
            daily_data['is_weekend'] = daily_data['day_of_week'].isin([5, 6]).astype(int)
            
            # Add lag features
            for lag in [1, 7, 14, 30]:
                if len(daily_data) > lag:
                    daily_data[f'cost_lag_{lag}'] = daily_data['total_cost'].shift(lag)
            
            # Add rolling statistics
            for window in [7, 14, 30]:
                if len(daily_data) > window:
                    daily_data[f'cost_ma_{window}'] = daily_data['total_cost'].rolling(window).mean()
                    daily_data[f'cost_std_{window}'] = daily_data['total_cost'].rolling(window).std()
            
            # Add trend features
            daily_data['days_since_start'] = (daily_data['date'] - daily_data['date'].min()).dt.days
            
            # Remove rows with NaN values (due to lag/rolling features)
            daily_data = daily_data.dropna()
            
            return daily_data
            
        except Exception as e:
            raise AnalyzerError(f"Failed to prepare forecast data: {e}")
    
    def _select_best_model(self, data: pd.DataFrame) -> str:
        """Select the best forecasting model based on cross-validation."""
        try:
            # Prepare features and target
            feature_columns = [col for col in data.columns if col not in ['date', 'total_cost']]
            X = data[feature_columns]
            y = data['total_cost']
            
            # Simple train/test split
            split_point = int(len(data) * 0.8)
            X_train, X_test = X[:split_point], X[split_point:]
            y_train, y_test = y[:split_point], y[split_point:]
            
            best_model = 'linear'
            best_score = float('inf')
            
            for model_name, model in self.models.items():
                try:
                    # Train model
                    model.fit(X_train, y_train)
                    
                    # Make predictions
                    y_pred = model.predict(X_test)
                    
                    # Calculate error
                    mae = mean_absolute_error(y_test, y_pred)
                    
                    if mae < best_score:
                        best_score = mae
                        best_model = model_name
                        
                except Exception:
                    continue
            
            return best_model
            
        except Exception:
            return 'linear'  # Fallback to linear model
    
    def _train_and_forecast(self, data: pd.DataFrame, forecast_days: int, model_name: str) -> ForecastResult:
        """Train model and generate forecast."""
        try:
            # Prepare features and target
            feature_columns = [col for col in data.columns if col not in ['date', 'total_cost']]
            X = data[feature_columns]
            y = data['total_cost']
            
            # Train model
            model = self.models[model_name]
            model.fit(X, y)
            
            # Generate future dates
            last_date = data['date'].max()
            forecast_dates = [last_date + timedelta(days=i+1) for i in range(forecast_days)]
            
            # Prepare future features
            future_features = []
            for i, forecast_date in enumerate(forecast_dates):
                features = {
                    'day_of_week': forecast_date.dayofweek,
                    'day_of_month': forecast_date.day,
                    'month': forecast_date.month,
                    'quarter': (forecast_date.month - 1) // 3 + 1,
                    'is_weekend': int(forecast_date.dayofweek in [5, 6]),
                    'days_since_start': (forecast_date - data['date'].min()).days
                }
                
                # Add lag features (use recent actual values)
                for lag in [1, 7, 14, 30]:
                    if len(data) >= lag:
                        features[f'cost_lag_{lag}'] = data['total_cost'].iloc[-lag]
                    else:
                        features[f'cost_lag_{lag}'] = data['total_cost'].iloc[-1]
                
                # Add rolling features
                for window in [7, 14, 30]:
                    if len(data) >= window:
                        features[f'cost_ma_{window}'] = data['total_cost'].tail(window).mean()
                        features[f'cost_std_{window}'] = data['total_cost'].tail(window).std()
                    else:
                        features[f'cost_ma_{window}'] = data['total_cost'].mean()
                        features[f'cost_std_{window}'] = data['total_cost'].std()
                
                future_features.append(features)
            
            future_df = pd.DataFrame(future_features)
            
            # Ensure all required columns are present
            for col in feature_columns:
                if col not in future_df.columns:
                    future_df[col] = 0
            
            # Make predictions
            forecast_values = model.predict(future_df[feature_columns])
            
            # Calculate confidence intervals (simplified)
            residuals = y - model.predict(X)
            std_error = np.std(residuals)
            confidence_intervals = [(val - 1.96*std_error, val + 1.96*std_error) for val in forecast_values]
            
            # Calculate accuracy metrics
            y_pred = model.predict(X)
            mae = mean_absolute_error(y, y_pred)
            mse = mean_squared_error(y, y_pred)
            rmse = np.sqrt(mse)
            
            accuracy_metrics = {
                'mae': mae,
                'mse': mse,
                'rmse': rmse,
                'mape': np.mean(np.abs((y - y_pred) / y)) * 100 if np.mean(y) > 0 else 0
            }
            
            # Feature importance (for tree-based models)
            feature_importance = None
            if hasattr(model, 'feature_importances_'):
                feature_importance = dict(zip(feature_columns, model.feature_importances_))
            
            # Assumptions
            assumptions = [
                f"Forecast based on {model_name} model",
                f"Trained on {len(data)} days of historical data",
                "Assumes similar usage patterns continue",
                "Confidence intervals based on historical prediction errors"
            ]
            
            return ForecastResult(
                forecast_values=forecast_values.tolist(),
                forecast_dates=forecast_dates,
                confidence_intervals=confidence_intervals,
                model_used=model_name,
                accuracy_metrics=accuracy_metrics,
                feature_importance=feature_importance,
                assumptions=assumptions
            )
            
        except Exception as e:
            raise AnalyzerError(f"Failed to train and forecast: {e}")
    
    def _assess_budget_risk(self, variance: float, budget: float) -> str:
        """Assess budget risk level."""
        if budget == 0:
            return "high"
        
        variance_percentage = abs(variance) / budget * 100
        
        if variance_percentage > 20:
            return "critical"
        elif variance_percentage > 10:
            return "high"
        elif variance_percentage > 5:
            return "medium"
        else:
            return "low"
    
    def _calculate_overrun_probability(self, forecast: ForecastResult, budget: float) -> float:
        """Calculate probability of budget overrun."""
        try:
            # Simple calculation based on forecast distribution
            forecast_mean = np.mean(forecast.forecast_values)
            forecast_std = np.std(forecast.forecast_values)
            
            if forecast_std == 0:
                return 1.0 if forecast_mean > budget else 0.0
            
            # Z-score for budget
            z_score = (budget - forecast_mean) / forecast_std
            
            # Probability of exceeding budget
            overrun_prob = 1 - self._normal_cdf(z_score)
            
            return max(0.0, min(1.0, overrun_prob))
            
        except Exception:
            return 0.5  # Default to 50% if calculation fails
    
    def _normal_cdf(self, x: float) -> float:
        """Normal cumulative distribution function."""
        return 0.5 * (1 + np.erf(x / np.sqrt(2)))
    
    def _recommend_budget_adjustment(self, forecasted_spend: float, current_budget: float) -> float:
        """Recommended budget adjustment."""
        # Add 10% buffer to forecasted spend
        recommended = forecasted_spend * 1.1
        
        # Round to reasonable precision
        return round(recommended, 2)
    
    def _identify_cost_saving_opportunities(self, billing_data: List[BillingData]) -> List[str]:
        """Identify potential cost saving opportunities."""
        opportunities = []
        
        df = pd.DataFrame([self._billing_data_to_dict(data) for data in billing_data])
        
        # Check for idle resources
        if 'resource_type' in df.columns:
            resource_types = df['resource_type'].value_counts()
            
            for resource_type, count in resource_types.items():
                if 'instance' in resource_type.lower() and count > 10:
                    opportunities.append(f"Consider rightsizing or scheduling {count} {resource_type}s")
        
        # Check for high-cost services
        service_costs = df.groupby('service')['cost'].sum()
        high_cost_services = service_costs[service_costs > service_costs.quantile(0.8)]
        
        for service, cost in high_cost_services.items():
            opportunities.append(f"Review {service} usage - ${cost:.2f} total cost")
        
        # Check for regional cost optimization
        if 'region' in df.columns:
            regional_costs = df.groupby('region')['cost'].sum()
            expensive_regions = regional_costs[regional_costs > regional_costs.quantile(0.8)]
            
            for region, cost in expensive_regions.items():
                opportunities.append(f"Consider alternative regions for {region} - ${cost:.2f} total cost")
        
        return opportunities
    
    def _apply_scenario_adjustments(self, billing_data: List[BillingData], 
                                  scenario_params: Dict[str, float]) -> List[BillingData]:
        """Apply scenario adjustments to billing data."""
        adjusted_data = []
        
        for data in billing_data:
            # Create a copy of the data
            adjusted = BillingData(
                provider=data.provider,
                account_id=data.account_id,
                service=data.service,
                region=data.region,
                resource_id=data.resource_id,
                resource_name=data.resource_name,
                usage_type=data.usage_type,
                usage_amount=data.usage_amount,
                usage_unit=data.usage_unit,
                cost=data.cost,
                currency=data.currency,
                start_time=data.start_time,
                end_time=data.end_time,
                tags=data.tags.copy(),
                environment=data.environment,
                cost_center=data.cost_center
            )
            
            # Apply adjustments
            if 'cost_multiplier' in scenario_params:
                adjusted.cost *= scenario_params['cost_multiplier']
            
            if 'usage_multiplier' in scenario_params:
                adjusted.usage_amount *= scenario_params['usage_multiplier']
            
            adjusted_data.append(adjusted)
        
        return adjusted_data
    
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
