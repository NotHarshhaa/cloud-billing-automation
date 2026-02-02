"""
Cost optimization recommendations engine.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from enum import Enum

from ..core.config import Config
from ..core.exceptions import AnalyzerError
from ..collectors.base import BillingData, ResourceData
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class RecommendationType(Enum):
    """Types of cost optimization recommendations."""
    RIGHTSIZING = "rightsizing"
    SCHEDULED_SHUTDOWN = "scheduled_shutdown"
    UNUSED_RESOURCES = "unused_resources"
    STORAGE_OPTIMIZATION = "storage_optimization"
    NETWORK_OPTIMIZATION = "network_optimization"
    RESERVED_INSTANCES = "reserved_instances"
    SPOT_INSTANCES = "spot_instances"
    TAG_COMPLIANCE = "tag_compliance"


@dataclass
class CostRecommendation:
    """Cost optimization recommendation."""
    title: str
    description: str
    recommendation_type: RecommendationType
    potential_savings: float
    currency: str
    resource_id: str
    resource_type: str
    provider: str
    confidence_score: float
    effort_level: str  # low, medium, high
    implementation_steps: List[str]
    risk_level: str  # low, medium, high


class CostOptimizer:
    """Cost optimization and recommendations engine."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
    
    def analyze_costs_for_optimization(self, billing_data: List[BillingData], 
                                      resource_data: List[ResourceData]) -> List[CostRecommendation]:
        """Analyze billing and resource data to generate optimization recommendations."""
        recommendations = []
        
        try:
            self.logger.info("Starting cost optimization analysis")
            
            # Rightsizing recommendations
            rightsizing_recs = self._analyze_rightsizing_opportunities(billing_data, resource_data)
            recommendations.extend(rightsizing_recs)
            
            # Unused resources recommendations
            unused_recs = self._identify_unused_resources(resource_data, billing_data)
            recommendations.extend(unused_recs)
            
            # Scheduled shutdown recommendations
            shutdown_recs = self._analyze_scheduled_shutdown_opportunities(resource_data, billing_data)
            recommendations.extend(shutdown_recs)
            
            # Storage optimization recommendations
            storage_recs = self._analyze_storage_optimization(billing_data, resource_data)
            recommendations.extend(storage_recs)
            
            # Reserved instances recommendations
            reserved_recs = self._analyze_reserved_instance_opportunities(billing_data, resource_data)
            recommendations.extend(reserved_recs)
            
            # Tag compliance recommendations
            tag_recs = self._analyze_tag_compliance(resource_data)
            recommendations.extend(tag_recs)
            
            # Sort by potential savings (highest first)
            recommendations.sort(key=lambda x: x.potential_savings, reverse=True)
            
            self.logger.info(f"Generated {len(recommendations)} cost optimization recommendations")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error in cost optimization analysis: {e}", exc_info=True)
            raise AnalyzerError(f"Failed to analyze costs for optimization: {e}")
    
    def _analyze_rightsizing_opportunities(self, billing_data: List[BillingData], 
                                         resource_data: List[ResourceData]) -> List[CostRecommendation]:
        """Identify rightsizing opportunities for compute resources."""
        recommendations = []
        
        # Group compute resources by type and analyze utilization
        compute_resources = [r for r in resource_data if 
                            r.resource_type.lower() in ['ec2', 'vm', 'compute', 'instance']]
        
        for resource in compute_resources:
            # Find corresponding billing data
            resource_costs = [b for b in billing_data if b.resource_id == resource.resource_id]
            if not resource_costs:
                continue
            
            monthly_cost = sum(b.cost for b in resource_costs if 
                            (datetime.now() - b.start_time).days <= 30)
            
            # Simple heuristic: if cost is high but resource appears underutilized
            if monthly_cost > 100 and resource.is_idle:
                potential_savings = monthly_cost * 0.7  # Estimate 70% savings
                
                recommendation = CostRecommendation(
                    title=f"Rightsize or terminate {resource.resource_type}",
                    description=f"Resource {resource.resource_name} appears to be idle but costs ${monthly_cost:.2f}/month",
                    recommendation_type=RecommendationType.RIGHTSIZING,
                    potential_savings=potential_savings,
                    currency="USD",
                    resource_id=resource.resource_id,
                    resource_type=resource.resource_type,
                    provider=resource.provider,
                    confidence_score=0.8,
                    effort_level="medium",
                    implementation_steps=[
                        "Verify resource utilization metrics",
                        "Consider downsizing to smaller instance type",
                        "Evaluate if resource can be terminated",
                        "Implement auto-scaling if applicable"
                    ],
                    risk_level="low"
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    def _identify_unused_resources(self, resource_data: List[ResourceData], 
                                 billing_data: List[BillingData]) -> List[CostRecommendation]:
        """Identify completely unused resources that can be terminated."""
        recommendations = []
        
        for resource in resource_data:
            if resource.is_idle:
                # Find associated costs
                resource_costs = [b for b in billing_data if b.resource_id == resource.resource_id]
                if not resource_costs:
                    continue
                
                monthly_cost = sum(b.cost for b in resource_costs if 
                                (datetime.now() - b.start_time).days <= 30)
                
                if monthly_cost > 10:  # Only recommend if cost is significant
                    recommendation = CostRecommendation(
                        title=f"Terminate unused {resource.resource_type}",
                        description=f"Resource {resource.resource_name} has been idle and costs ${monthly_cost:.2f}/month",
                        recommendation_type=RecommendationType.UNUSED_RESOURCES,
                        potential_savings=monthly_cost,
                        currency="USD",
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        provider=resource.provider,
                        confidence_score=0.9,
                        effort_level="low",
                        implementation_steps=[
                            "Confirm resource is not needed",
                            "Take backup if necessary",
                            "Terminate resource",
                            "Update documentation"
                        ],
                        risk_level="low"
                    )
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_scheduled_shutdown_opportunities(self, resource_data: List[ResourceData], 
                                               billing_data: List[BillingData]) -> List[CostRecommendation]:
        """Identify resources that could benefit from scheduled shutdown."""
        recommendations = []
        
        # Look for development/test resources that run 24/7
        dev_resources = [r for r in resource_data if 
                        r.environment and r.environment.lower() in ['dev', 'test', 'staging']]
        
        for resource in dev_resources:
            if not resource.is_idle:  # Active but could be scheduled
                resource_costs = [b for b in billing_data if b.resource_id == resource.resource_id]
                if not resource_costs:
                    continue
                
                monthly_cost = sum(b.cost for b in resource_costs if 
                                (datetime.now() - b.start_time).days <= 30)
                
                # Assume 12 hours/day usage for dev environments
                potential_savings = monthly_cost * 0.5  # 50% savings with 12-hour schedule
                
                recommendation = CostRecommendation(
                    title=f"Implement scheduled shutdown for {resource.resource_type}",
                    description=f"Development resource {resource.resource_name} could benefit from scheduled shutdown",
                    recommendation_type=RecommendationType.SCHEDULED_SHUTDOWN,
                    potential_savings=potential_savings,
                    currency="USD",
                    resource_id=resource.resource_id,
                    resource_type=resource.resource_type,
                    provider=resource.provider,
                    confidence_score=0.7,
                    effort_level="medium",
                    implementation_steps=[
                        "Define shutdown schedule (e.g., 7 PM - 7 AM)",
                        "Configure auto-start/stop scripts",
                        "Test schedule functionality",
                        "Monitor for any issues"
                    ],
                    risk_level="low"
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_storage_optimization(self, billing_data: List[BillingData], 
                                    resource_data: List[ResourceData]) -> List[CostRecommendation]:
        """Analyze storage costs for optimization opportunities."""
        recommendations = []
        
        # Group storage costs by service
        storage_services = ['s3', 'blob', 'storage', 'ebs', 'disk']
        storage_costs = {}
        
        for billing in billing_data:
            if any(service in billing.service.lower() for service in storage_services):
                if billing.service not in storage_costs:
                    storage_costs[billing.service] = 0
                storage_costs[billing.service] += billing.cost
        
        # Recommend storage optimizations for high-cost services
        for service, cost in storage_costs.items():
            if cost > 50:  # Significant storage cost
                potential_savings = cost * 0.3  # Estimate 30% savings with optimization
                
                recommendation = CostRecommendation(
                    title=f"Optimize {service} storage costs",
                    description=f"Storage service {service} costs ${cost:.2f}/month and could be optimized",
                    recommendation_type=RecommendationType.STORAGE_OPTIMIZATION,
                    potential_savings=potential_savings,
                    currency="USD",
                    resource_id="storage-optimization",
                    resource_type="storage",
                    provider="multiple",
                    confidence_score=0.6,
                    effort_level="medium",
                    implementation_steps=[
                        "Review storage lifecycle policies",
                        "Implement data archiving for old data",
                        "Use appropriate storage tiers",
                        "Clean up unused storage volumes"
                    ],
                    risk_level="low"
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_reserved_instance_opportunities(self, billing_data: List[BillingData], 
                                               resource_data: List[ResourceData]) -> List[CostRecommendation]:
        """Analyze opportunities for reserved instances/commitments."""
        recommendations = []
        
        # Find long-running compute instances
        compute_services = ['ec2', 'vm', 'compute']
        long_running_resources = {}
        
        for resource in resource_data:
            if any(service in resource.resource_type.lower() for service in compute_services):
                if not resource.is_idle and resource.environment and resource.environment.lower() == 'production':
                    # Check if resource has been running for a while
                    if (datetime.now() - resource.creation_time).days > 30:
                        resource_costs = [b for b in billing_data if b.resource_id == resource.resource_id]
                        monthly_cost = sum(b.cost for b in resource_costs if 
                                        (datetime.now() - b.start_time).days <= 30)
                        
                        if monthly_cost > 50:
                            long_running_resources[resource.resource_id] = monthly_cost
        
        # Recommend reserved instances for long-running resources
        for resource_id, monthly_cost in long_running_resources.items():
            potential_savings = monthly_cost * 0.4  # Estimate 40% savings with reserved instances
            
            recommendation = CostRecommendation(
                title="Purchase reserved instances",
                description=f"Long-running compute resource could benefit from reserved instance pricing",
                recommendation_type=RecommendationType.RESERVED_INSTANCES,
                potential_savings=potential_savings,
                currency="USD",
                resource_id=resource_id,
                resource_type="compute",
                provider="aws",  # Could be extended for other providers
                confidence_score=0.8,
                effort_level="medium",
                implementation_steps=[
                    "Analyze usage patterns",
                    "Choose appropriate reservation term",
                    "Purchase reserved instances",
                    "Monitor savings"
                ],
                risk_level="medium"
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_tag_compliance(self, resource_data: List[ResourceData]) -> List[CostRecommendation]:
        """Analyze tag compliance and recommend improvements."""
        recommendations = []
        
        # Check for missing required tags
        required_tags = self.config.aws.tags_required  # Could be extended for other providers
        
        for resource in resource_data:
            missing_tags = [tag for tag in required_tags if tag not in resource.tags]
            
            if missing_tags:
                # Estimate potential cost of poor tagging (hard to quantify, use fixed amount)
                potential_savings = 20.0  # Fixed amount for compliance improvement
                
                recommendation = CostRecommendation(
                    title=f"Improve resource tagging compliance",
                    description=f"Resource {resource.resource_name} is missing required tags: {', '.join(missing_tags)}",
                    recommendation_type=RecommendationType.TAG_COMPLIANCE,
                    potential_savings=potential_savings,
                    currency="USD",
                    resource_id=resource.resource_id,
                    resource_type=resource.resource_type,
                    provider=resource.provider,
                    confidence_score=0.9,
                    effort_level="low",
                    implementation_steps=[
                        f"Add missing tags: {', '.join(missing_tags)}",
                        "Implement tagging policies",
                        "Set up automated tagging",
                        "Monitor compliance"
                    ],
                    risk_level="low"
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    def generate_optimization_report(self, recommendations: List[CostRecommendation]) -> Dict[str, Any]:
        """Generate a comprehensive optimization report."""
        if not recommendations:
            return {"message": "No optimization recommendations available"}
        
        # Calculate total potential savings
        total_savings = sum(r.potential_savings for r in recommendations)
        
        # Group recommendations by type
        by_type = {}
        for rec in recommendations:
            if rec.recommendation_type not in by_type:
                by_type[rec.recommendation_type] = []
            by_type[rec.recommendation_type].append(rec)
        
        # Group by effort level
        by_effort = {"low": [], "medium": [], "high": []}
        for rec in recommendations:
            by_effort[rec.effort_level].append(rec)
        
        # Group by risk level
        by_risk = {"low": [], "medium": [], "high": []}
        for rec in recommendations:
            by_risk[rec.risk_level].append(rec)
        
        return {
            "summary": {
                "total_recommendations": len(recommendations),
                "total_potential_savings": total_savings,
                "currency": "USD",
                "average_savings_per_recommendation": total_savings / len(recommendations)
            },
            "recommendations_by_type": {
                rec_type.value: {
                    "count": len(recs),
                    "potential_savings": sum(r.potential_savings for r in recs),
                    "recommendations": recs
                }
                for rec_type, recs in by_type.items()
            },
            "recommendations_by_effort": {
                effort: {
                    "count": len(recs),
                    "potential_savings": sum(r.potential_savings for r in recs),
                    "recommendations": recs
                }
                for effort, recs in by_effort.items()
            },
            "recommendations_by_risk": {
                risk: {
                    "count": len(recs),
                    "potential_savings": sum(r.potential_savings for r in recs),
                    "recommendations": recs
                }
                for risk, recs in by_risk.items()
            },
            "top_recommendations": recommendations[:10],  # Top 10 by savings
            "quick_wins": [r for r in recommendations if r.effort_level == "low" and r.risk_level == "low"]
        }
