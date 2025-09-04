#!/usr/bin/env python3
"""
Priority 28: CONSTEL - Cost Estimator
Estimates build-time, run-time, and scaling costs of user-designed systems
"""

import json
import uuid
import sqlite3
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import logging
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CostModel(Enum):
    """Types of cost models"""
    BUILD_TIME = "build_time"
    RUNTIME = "runtime"
    SCALING = "scaling"
    STORAGE = "storage"
    API_CALLS = "api_calls"
    COMPUTE = "compute"
    BANDWIDTH = "bandwidth"

class PricingTier(Enum):
    """Pricing tiers for different services"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

class ServiceProvider(Enum):
    """Service providers for cost estimation"""
    OPENAI = "openai"
    GOOGLE_CLOUD = "google_cloud"
    AWS = "aws"
    AZURE = "azure"
    CUSTOM = "custom"


class CostType(str, Enum):
    """Types of costs"""
    BUILD = "build"
    RUNTIME = "runtime"
    SCALING = "scaling"
    MAINTENANCE = "maintenance"
    LICENSING = "licensing"


@dataclass
class CostBreakdown:
    """Detailed cost breakdown"""
    breakdown_id: str
    estimate_id: str
    cost_type: CostType
    amount: float
    currency: str
    period: str
    details: Dict[str, Any]
    created_at: datetime


@dataclass
class CostProjection:
    """Cost projection over time"""
    projection_id: str
    system_id: str
    period_months: int
    monthly_costs: List[float]
    cumulative_costs: List[float]
    growth_rate: float
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class CostEstimate:
    """Represents a cost estimate"""
    estimate_id: str
    system_id: str
    estimate_date: datetime
    cost_model: CostModel
    monthly_cost: float
    annual_cost: float
    breakdown: Dict[str, float]
    assumptions: Dict[str, Any]
    confidence_level: float  # 0-1, higher is more confident
    provider: ServiceProvider
    pricing_tier: PricingTier
    metadata: Dict[str, Any]

@dataclass
class SystemCostProfile:
    """Represents the complete cost profile for a system"""
    system_id: str
    build_cost: float
    monthly_runtime_cost: float
    annual_runtime_cost: float
    scaling_cost_per_user: float
    storage_cost_per_gb: float
    api_cost_per_call: float
    compute_cost_per_hour: float
    bandwidth_cost_per_gb: float
    total_first_year_cost: float
    cost_breakdown: Dict[str, float]
    recommendations: List[str]

class CostEstimator:
    """Estimates costs for building, running, and scaling systems"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "compliance.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for database operations
        self.db_lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Load pricing data
        self.pricing_data = self._load_pricing_data()
        
        logger.info("Cost Estimator initialized")
    
    def _init_database(self):
        """Initialize the cost estimation database"""
        with sqlite3.connect(self.db_path) as conn:
            # Cost estimates table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_estimates (
                    estimate_id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    estimate_date TEXT NOT NULL,
                    cost_model TEXT NOT NULL,
                    monthly_cost REAL NOT NULL,
                    annual_cost REAL NOT NULL,
                    breakdown TEXT NOT NULL,
                    assumptions TEXT NOT NULL,
                    confidence_level REAL NOT NULL,
                    provider TEXT NOT NULL,
                    pricing_tier TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # System cost profiles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_cost_profiles (
                    system_id TEXT PRIMARY KEY,
                    build_cost REAL NOT NULL,
                    monthly_runtime_cost REAL NOT NULL,
                    annual_runtime_cost REAL NOT NULL,
                    scaling_cost_per_user REAL NOT NULL,
                    storage_cost_per_gb REAL NOT NULL,
                    api_cost_per_call REAL NOT NULL,
                    compute_cost_per_hour REAL NOT NULL,
                    bandwidth_cost_per_gb REAL NOT NULL,
                    total_first_year_cost REAL NOT NULL,
                    cost_breakdown TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_estimates_system ON cost_estimates(system_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_estimates_date ON cost_estimates(estimate_date)")
    
    def _load_pricing_data(self) -> Dict[str, Dict[str, Any]]:
        """Load pricing data for different services"""
        pricing_data = {
            ServiceProvider.OPENAI.value: {
                "gpt-4": {
                    "input_cost_per_1k_tokens": 0.03,
                    "output_cost_per_1k_tokens": 0.06,
                    "tier": PricingTier.PROFESSIONAL
                },
                "gpt-3.5-turbo": {
                    "input_cost_per_1k_tokens": 0.0015,
                    "output_cost_per_1k_tokens": 0.002,
                    "tier": PricingTier.BASIC
                },
                "embedding-ada-002": {
                    "cost_per_1k_tokens": 0.0001,
                    "tier": PricingTier.BASIC
                }
            },
            ServiceProvider.GOOGLE_CLOUD.value: {
                "compute_engine": {
                    "n1-standard-1": 0.0475,  # per hour
                    "n1-standard-2": 0.095,
                    "n1-standard-4": 0.19,
                    "tier": PricingTier.PROFESSIONAL
                },
                "cloud_storage": {
                    "standard": 0.02,  # per GB per month
                    "nearline": 0.01,
                    "coldline": 0.004,
                    "tier": PricingTier.BASIC
                },
                "cloud_functions": {
                    "invocations": 0.0000004,  # per invocation
                    "cpu_time": 0.0000025,  # per 100ms
                    "memory_time": 0.0000025,  # per GB-second
                    "tier": PricingTier.BASIC
                }
            },
            ServiceProvider.AWS.value: {
                "ec2": {
                    "t3.micro": 0.0104,  # per hour
                    "t3.small": 0.0208,
                    "t3.medium": 0.0416,
                    "tier": PricingTier.PROFESSIONAL
                },
                "s3": {
                    "standard": 0.023,  # per GB per month
                    "infrequent_access": 0.0125,
                    "glacier": 0.004,
                    "tier": PricingTier.BASIC
                },
                "lambda": {
                    "requests": 0.20,  # per 1M requests
                    "duration": 0.0000166667,  # per GB-second
                    "tier": PricingTier.BASIC
                }
            }
        }
        
        return pricing_data
    
    def estimate_system_costs(self, system_id: str, system_config: Dict[str, Any],
                            user_count: int = 1000, data_volume_gb: float = 100.0) -> SystemCostProfile:
        """Estimate comprehensive costs for a system"""
        try:
            # Estimate build costs
            build_cost = self._estimate_build_cost(system_config)
            
            # Estimate runtime costs
            monthly_runtime_cost = self._estimate_runtime_cost(system_config, user_count, data_volume_gb)
            annual_runtime_cost = monthly_runtime_cost * 12
            
            # Estimate scaling costs
            scaling_cost_per_user = self._estimate_scaling_cost_per_user(system_config)
            
            # Estimate storage costs
            storage_cost_per_gb = self._estimate_storage_cost(system_config)
            
            # Estimate API costs
            api_cost_per_call = self._estimate_api_cost_per_call(system_config)
            
            # Estimate compute costs
            compute_cost_per_hour = self._estimate_compute_cost_per_hour(system_config)
            
            # Estimate bandwidth costs
            bandwidth_cost_per_gb = self._estimate_bandwidth_cost(system_config)
            
            # Calculate total first year cost
            total_first_year_cost = build_cost + annual_runtime_cost
            
            # Generate cost breakdown
            cost_breakdown = {
                "build_cost": build_cost,
                "monthly_runtime": monthly_runtime_cost,
                "annual_runtime": annual_runtime_cost,
                "scaling_per_user": scaling_cost_per_user,
                "storage_per_gb": storage_cost_per_gb,
                "api_per_call": api_cost_per_call,
                "compute_per_hour": compute_cost_per_hour,
                "bandwidth_per_gb": bandwidth_cost_per_gb
            }
            
            # Generate recommendations
            recommendations = self._generate_cost_recommendations(system_config, cost_breakdown)
            
            profile = SystemCostProfile(
                system_id=system_id,
                build_cost=build_cost,
                monthly_runtime_cost=monthly_runtime_cost,
                annual_runtime_cost=annual_runtime_cost,
                scaling_cost_per_user=scaling_cost_per_user,
                storage_cost_per_gb=storage_cost_per_gb,
                api_cost_per_call=api_cost_per_call,
                compute_cost_per_hour=compute_cost_per_hour,
                bandwidth_cost_per_gb=bandwidth_cost_per_gb,
                total_first_year_cost=total_first_year_cost,
                cost_breakdown=cost_breakdown,
                recommendations=recommendations
            )
            
            # Store cost profile
            self._store_cost_profile(profile)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error estimating system costs: {e}")
            raise
    
    def _estimate_build_cost(self, system_config: Dict[str, Any]) -> float:
        """Estimate build-time costs"""
        build_cost = 0.0
        
        # Development time cost (assuming $100/hour developer cost)
        development_hours = self._estimate_development_hours(system_config)
        build_cost += development_hours * 100
        
        # Infrastructure setup cost
        infrastructure_cost = self._estimate_infrastructure_setup_cost(system_config)
        build_cost += infrastructure_cost
        
        # Testing and validation cost
        testing_cost = self._estimate_testing_cost(system_config)
        build_cost += testing_cost
        
        return build_cost
    
    def _estimate_development_hours(self, system_config: Dict[str, Any]) -> float:
        """Estimate development hours based on system complexity"""
        hours = 0.0
        
        # Base hours for simple system
        hours += 40
        
        # Add hours for each component
        components = system_config.get("components", {})
        for component_name, component_config in components.items():
            complexity = component_config.get("complexity", "medium")
            if complexity == "low":
                hours += 8
            elif complexity == "medium":
                hours += 16
            elif complexity == "high":
                hours += 32
            elif complexity == "very_high":
                hours += 48
        
        # Add hours for AI/ML components
        ai_components = system_config.get("ai_models", [])
        hours += len(ai_components) * 24
        
        # Add hours for integration
        integrations = system_config.get("integrations", [])
        hours += len(integrations) * 12
        
        return hours
    
    def _estimate_infrastructure_setup_cost(self, system_config: Dict[str, Any]) -> float:
        """Estimate infrastructure setup cost"""
        cost = 0.0
        
        # Base infrastructure cost
        cost += 500
        
        # Add cost for each service
        services = system_config.get("services", [])
        for service in services:
            if service.get("type") == "database":
                cost += 200
            elif service.get("type") == "api_gateway":
                cost += 150
            elif service.get("type") == "load_balancer":
                cost += 300
            elif service.get("type") == "monitoring":
                cost += 100
        
        return cost
    
    def _estimate_testing_cost(self, system_config: Dict[str, Any]) -> float:
        """Estimate testing and validation cost"""
        cost = 0.0
        
        # Base testing cost
        cost += 200
        
        # Add cost for compliance testing
        if system_config.get("compliance_requirements"):
            cost += 500
        
        # Add cost for security testing
        if system_config.get("security_requirements"):
            cost += 400
        
        # Add cost for performance testing
        if system_config.get("performance_requirements"):
            cost += 300
        
        return cost
    
    def _estimate_runtime_cost(self, system_config: Dict[str, Any], 
                             user_count: int, data_volume_gb: float) -> float:
        """Estimate monthly runtime costs"""
        monthly_cost = 0.0
        
        # Compute costs
        compute_cost = self._estimate_compute_cost(system_config, user_count)
        monthly_cost += compute_cost
        
        # Storage costs
        storage_cost = self._estimate_storage_cost(system_config) * data_volume_gb
        monthly_cost += storage_cost
        
        # API costs
        api_cost = self._estimate_api_cost(system_config, user_count)
        monthly_cost += api_cost
        
        # Bandwidth costs
        bandwidth_cost = self._estimate_bandwidth_cost(system_config) * (user_count * 0.1)  # 100MB per user
        monthly_cost += bandwidth_cost
        
        # Third-party service costs
        third_party_cost = self._estimate_third_party_cost(system_config, user_count)
        monthly_cost += third_party_cost
        
        return monthly_cost
    
    def _estimate_compute_cost(self, system_config: Dict[str, Any], user_count: int) -> float:
        """Estimate compute costs"""
        cost = 0.0
        
        # Estimate compute hours based on user count
        compute_hours_per_month = 730  # 24/7 operation
        compute_intensity = system_config.get("compute_intensity", "medium")
        
        if compute_intensity == "low":
            instance_type = "t3.micro"
            instances_needed = max(1, user_count // 1000)
        elif compute_intensity == "medium":
            instance_type = "t3.small"
            instances_needed = max(1, user_count // 500)
        elif compute_intensity == "high":
            instance_type = "t3.medium"
            instances_needed = max(1, user_count // 250)
        else:
            instance_type = "t3.large"
            instances_needed = max(1, user_count // 100)
        
        # Get pricing from AWS (default)
        hourly_rate = self.pricing_data[ServiceProvider.AWS.value]["ec2"][instance_type]
        cost = hourly_rate * compute_hours_per_month * instances_needed
        
        return cost
    
    def _estimate_storage_cost(self, system_config: Dict[str, Any]) -> float:
        """Estimate storage cost per GB"""
        storage_type = system_config.get("storage_type", "standard")
        
        if storage_type == "standard":
            return self.pricing_data[ServiceProvider.AWS.value]["s3"]["standard"]
        elif storage_type == "infrequent_access":
            return self.pricing_data[ServiceProvider.AWS.value]["s3"]["infrequent_access"]
        elif storage_type == "glacier":
            return self.pricing_data[ServiceProvider.AWS.value]["s3"]["glacier"]
        else:
            return 0.023  # Default to standard S3 pricing
    
    def _estimate_api_cost(self, system_config: Dict[str, Any], user_count: int) -> float:
        """Estimate API costs"""
        cost = 0.0
        
        # Estimate API calls per user per month
        api_calls_per_user = system_config.get("api_calls_per_user", 100)
        total_api_calls = user_count * api_calls_per_user
        
        # Get API pricing
        api_provider = system_config.get("api_provider", ServiceProvider.OPENAI.value)
        api_model = system_config.get("api_model", "gpt-3.5-turbo")
        
        if api_provider == ServiceProvider.OPENAI.value:
            if api_model in self.pricing_data[api_provider]:
                pricing = self.pricing_data[api_provider][api_model]
                avg_tokens_per_call = system_config.get("avg_tokens_per_call", 1000)
                
                # Estimate input/output token ratio
                input_ratio = 0.7
                output_ratio = 0.3
                
                input_cost = (total_api_calls * avg_tokens_per_call * input_ratio * 
                             pricing["input_cost_per_1k_tokens"] / 1000)
                output_cost = (total_api_calls * avg_tokens_per_call * output_ratio * 
                              pricing["output_cost_per_1k_tokens"] / 1000)
                
                cost = input_cost + output_cost
        
        return cost
    
    def _estimate_bandwidth_cost(self, system_config: Dict[str, Any]) -> float:
        """Estimate bandwidth cost per GB"""
        # Default to AWS pricing
        return 0.09  # $0.09 per GB
    
    def _estimate_third_party_cost(self, system_config: Dict[str, Any], user_count: int) -> float:
        """Estimate third-party service costs"""
        cost = 0.0
        
        # Add costs for each third-party service
        third_party_services = system_config.get("third_party_services", [])
        for service in third_party_services:
            service_type = service.get("type", "")
            service_tier = service.get("tier", PricingTier.BASIC)
            
            if service_type == "analytics":
                if service_tier == PricingTier.BASIC:
                    cost += 25
                elif service_tier == PricingTier.PROFESSIONAL:
                    cost += 100
                elif service_tier == PricingTier.ENTERPRISE:
                    cost += 500
            elif service_type == "monitoring":
                if service_tier == PricingTier.BASIC:
                    cost += 15
                elif service_tier == PricingTier.PROFESSIONAL:
                    cost += 50
                elif service_tier == PricingTier.ENTERPRISE:
                    cost += 200
            elif service_type == "email":
                cost += user_count * 0.01  # $0.01 per user per month
        
        return cost
    
    def _estimate_scaling_cost_per_user(self, system_config: Dict[str, Any]) -> float:
        """Estimate scaling cost per additional user"""
        cost = 0.0
        
        # Compute scaling cost
        compute_intensity = system_config.get("compute_intensity", "medium")
        if compute_intensity == "low":
            cost += 0.01
        elif compute_intensity == "medium":
            cost += 0.02
        elif compute_intensity == "high":
            cost += 0.05
        else:
            cost += 0.10
        
        # Storage scaling cost
        cost += 0.0001  # $0.0001 per user for storage
        
        # API scaling cost
        api_calls_per_user = system_config.get("api_calls_per_user", 100)
        cost += api_calls_per_user * 0.0001  # $0.0001 per API call
        
        return cost
    
    def _estimate_compute_cost_per_hour(self, system_config: Dict[str, Any]) -> float:
        """Estimate compute cost per hour"""
        compute_intensity = system_config.get("compute_intensity", "medium")
        
        if compute_intensity == "low":
            return self.pricing_data[ServiceProvider.AWS.value]["ec2"]["t3.micro"]
        elif compute_intensity == "medium":
            return self.pricing_data[ServiceProvider.AWS.value]["ec2"]["t3.small"]
        elif compute_intensity == "high":
            return self.pricing_data[ServiceProvider.AWS.value]["ec2"]["t3.medium"]
        else:
            return self.pricing_data[ServiceProvider.AWS.value]["ec2"]["t3.large"]
    
    def _estimate_api_cost_per_call(self, system_config: Dict[str, Any]) -> float:
        """Estimate API cost per call"""
        api_provider = system_config.get("api_provider", ServiceProvider.OPENAI.value)
        api_model = system_config.get("api_model", "gpt-3.5-turbo")
        avg_tokens_per_call = system_config.get("avg_tokens_per_call", 1000)
        
        if api_provider == ServiceProvider.OPENAI.value:
            if api_model in self.pricing_data[api_provider]:
                pricing = self.pricing_data[api_provider][api_model]
                input_ratio = 0.7
                output_ratio = 0.3
                
                input_cost = (avg_tokens_per_call * input_ratio * 
                             pricing["input_cost_per_1k_tokens"] / 1000)
                output_cost = (avg_tokens_per_call * output_ratio * 
                              pricing["output_cost_per_1k_tokens"] / 1000)
                
                return input_cost + output_cost
        
        return 0.002  # Default cost per call
    
    def _generate_cost_recommendations(self, system_config: Dict[str, Any], 
                                     cost_breakdown: Dict[str, float]) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        # Check for high compute costs
        if cost_breakdown["compute_per_hour"] > 0.05:
            recommendations.append("Consider using spot instances for non-critical workloads")
            recommendations.append("Implement auto-scaling to optimize compute usage")
        
        # Check for high API costs
        if cost_breakdown["api_per_call"] > 0.01:
            recommendations.append("Implement caching to reduce API calls")
            recommendations.append("Consider using cheaper models for non-critical tasks")
        
        # Check for high storage costs
        if cost_breakdown["storage_per_gb"] > 0.05:
            recommendations.append("Use lifecycle policies to move data to cheaper storage tiers")
            recommendations.append("Implement data compression to reduce storage needs")
        
        # Check for high build costs
        if cost_breakdown["build_cost"] > 10000:
            recommendations.append("Consider using managed services to reduce development time")
            recommendations.append("Implement CI/CD to automate deployment and reduce manual work")
        
        # General recommendations
        recommendations.append("Monitor usage patterns and optimize based on actual usage")
        recommendations.append("Consider reserved instances for predictable workloads")
        recommendations.append("Implement cost alerts to prevent unexpected charges")
        
        return recommendations
    
    def _store_cost_profile(self, profile: SystemCostProfile):
        """Store cost profile in database"""
        with self.db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO system_cost_profiles (
                        system_id, build_cost, monthly_runtime_cost, annual_runtime_cost,
                        scaling_cost_per_user, storage_cost_per_gb, api_cost_per_call,
                        compute_cost_per_hour, bandwidth_cost_per_gb, total_first_year_cost,
                        cost_breakdown, recommendations, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile.system_id, profile.build_cost, profile.monthly_runtime_cost,
                    profile.annual_runtime_cost, profile.scaling_cost_per_user,
                    profile.storage_cost_per_gb, profile.api_cost_per_call,
                    profile.compute_cost_per_hour, profile.bandwidth_cost_per_gb,
                    profile.total_first_year_cost, json.dumps(profile.cost_breakdown),
                    json.dumps(profile.recommendations), datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
    
    def get_cost_history(self, system_id: str) -> List[Dict[str, Any]]:
        """Get cost estimation history for a system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM cost_estimates 
                    WHERE system_id = ? 
                    ORDER BY estimate_date DESC
                """, (system_id,))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        "estimate_id": row[0],
                        "estimate_date": row[2],
                        "cost_model": row[3],
                        "monthly_cost": row[4],
                        "annual_cost": row[5],
                        "confidence_level": row[8],
                        "provider": row[9],
                        "pricing_tier": row[10]
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting cost history: {e}")
            return []
    
    def update_pricing_data(self, provider: ServiceProvider, 
                           service_data: Dict[str, Any]):
        """Update pricing data for a service provider"""
        self.pricing_data[provider.value] = service_data
        logger.info(f"Updated pricing data for {provider.value}")
    
    def get_pricing_comparison(self, system_config: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Compare costs across different service providers"""
        comparison = {}
        
        providers = [ServiceProvider.AWS, ServiceProvider.GOOGLE_CLOUD, ServiceProvider.AZURE]
        
        for provider in providers:
            try:
                # Temporarily update pricing data for comparison
                original_pricing = self.pricing_data.copy()
                
                # Estimate costs for this provider
                profile = self.estimate_system_costs(
                    "comparison", system_config, user_count=1000, data_volume_gb=100.0
                )
                
                comparison[provider.value] = {
                    "monthly_cost": profile.monthly_runtime_cost,
                    "annual_cost": profile.annual_runtime_cost,
                    "build_cost": profile.build_cost,
                    "total_first_year": profile.total_first_year_cost
                }
                
                # Restore original pricing
                self.pricing_data = original_pricing
                
            except Exception as e:
                logger.error(f"Error comparing costs for {provider.value}: {e}")
                comparison[provider.value] = {"error": str(e)}
        
        return comparison
