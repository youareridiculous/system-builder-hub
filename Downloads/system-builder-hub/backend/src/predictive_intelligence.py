import os
import json
import time
import sqlite3
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
import logging
import statistics
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationType(Enum):
    SYSTEM_BUILD = "system_build"
    AGENT_CREATION = "agent_creation"
    TEMPLATE_DEVELOPMENT = "template_development"
    FEATURE_ADDITION = "feature_addition"
    INTEGRATION = "integration"
    OPTIMIZATION = "optimization"

class PerformanceMetric(Enum):
    DOWNLOADS = "downloads"
    REVENUE = "revenue"
    USAGE_TIME = "usage_time"
    USER_RETENTION = "user_retention"
    RATING = "rating"
    UPGRADES = "upgrades"

class MarketTrend(Enum):
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    EMERGING = "emerging"

class RLHFSignal(Enum):
    HELPFUL = "helpful"
    UNHELPFUL = "unhelpful"
    NEUTRAL = "neutral"

@dataclass
class BuildRecommendation:
    recommendation_id: str
    recommendation_type: RecommendationType
    title: str
    description: str
    confidence_score: float
    estimated_impact: str
    market_demand: float
    development_effort: str
    revenue_potential: float
    tags: List[str]
    categories: List[str]
    reasoning: str
    created_at: datetime
    is_implemented: bool
    implemented_at: Optional[datetime]

@dataclass
class PerformanceData:
    item_id: str
    item_type: str  # "system", "agent", "template"
    metric_type: PerformanceMetric
    value: float
    timestamp: datetime
    period: str  # "daily", "weekly", "monthly"
    context: Dict[str, Any]

@dataclass
class RevenueHeatmap:
    item_id: str
    item_type: str
    total_revenue: float
    revenue_trend: float  # percentage change
    download_count: int
    upgrade_count: int
    user_count: int
    average_rating: float
    market_trend: MarketTrend
    last_updated: datetime
    performance_metrics: Dict[str, float]

@dataclass
class ProfitAnalysis:
    item_id: str
    item_type: str
    total_revenue: float
    total_cost: float
    profit_margin: float
    roi: float
    break_even_point: datetime
    pricing_recommendation: str
    bundling_suggestions: List[str]
    market_position: str
    competitive_analysis: Dict[str, Any]

@dataclass
class RLHFTrainingData:
    data_id: str
    user_id: str
    system_id: str
    interaction_type: str
    user_action: str
    system_response: str
    user_feedback: RLHFSignal
    context: Dict[str, Any]
    timestamp: datetime
    confidence_score: float
    training_value: float

@dataclass
class MarketInsight:
    insight_id: str
    category: str
    trend: MarketTrend
    description: str
    confidence: float
    data_points: List[Dict[str, Any]]
    recommendations: List[str]
    created_at: datetime
    expires_at: datetime

class PredictiveIntelligenceEngine:
    def __init__(self, base_dir: str, llm_factory=None, agent_ecosystem=None, storefront=None, system_delivery=None):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data" / "predictive_intelligence"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Dependencies
        self.llm_factory = llm_factory
        self.agent_ecosystem = agent_ecosystem
        self.storefront = storefront
        self.system_delivery = system_delivery
        
        # Database
        self.db_path = self.data_dir / "predictive_intelligence.db"
        self._init_database()
        
        # Analysis state
        self.analysis_active = False
        self.recommendation_cache = {}
        self.performance_history = {}
        self.market_trends = {}
        
        # Start analysis thread
        self.analysis_thread = None
        self.start_analysis()
    
    def _init_database(self):
        """Initialize SQLite database for predictive intelligence data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build recommendations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS build_recommendations (
                recommendation_id TEXT PRIMARY KEY,
                recommendation_type TEXT,
                title TEXT,
                description TEXT,
                confidence_score REAL,
                estimated_impact TEXT,
                market_demand REAL,
                development_effort TEXT,
                revenue_potential REAL,
                tags TEXT,
                categories TEXT,
                reasoning TEXT,
                created_at TEXT,
                is_implemented INTEGER,
                implemented_at TEXT
            )
        ''')
        
        # Performance data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_data (
                data_id TEXT PRIMARY KEY,
                item_id TEXT,
                item_type TEXT,
                metric_type TEXT,
                value REAL,
                timestamp TEXT,
                period TEXT,
                context TEXT
            )
        ''')
        
        # Revenue heatmap table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_heatmap (
                item_id TEXT PRIMARY KEY,
                item_type TEXT,
                total_revenue REAL,
                revenue_trend REAL,
                download_count INTEGER,
                upgrade_count INTEGER,
                user_count INTEGER,
                average_rating REAL,
                market_trend TEXT,
                last_updated TEXT,
                performance_metrics TEXT
            )
        ''')
        
        # Profit analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profit_analysis (
                item_id TEXT PRIMARY KEY,
                item_type TEXT,
                total_revenue REAL,
                total_cost REAL,
                profit_margin REAL,
                roi REAL,
                break_even_point TEXT,
                pricing_recommendation TEXT,
                bundling_suggestions TEXT,
                market_position TEXT,
                competitive_analysis TEXT
            )
        ''')
        
        # RLHF training data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rlhf_training_data (
                data_id TEXT PRIMARY KEY,
                user_id TEXT,
                system_id TEXT,
                interaction_type TEXT,
                user_action TEXT,
                system_response TEXT,
                user_feedback TEXT,
                context TEXT,
                timestamp TEXT,
                confidence_score REAL,
                training_value REAL
            )
        ''')
        
        # Market insights table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_insights (
                insight_id TEXT PRIMARY KEY,
                category TEXT,
                trend TEXT,
                description TEXT,
                confidence REAL,
                data_points TEXT,
                recommendations TEXT,
                created_at TEXT,
                expires_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_analysis(self):
        """Start the analysis thread"""
        if not self.analysis_active:
            self.analysis_active = True
            self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
            self.analysis_thread.start()
            logger.info("Predictive intelligence analysis started")
    
    def stop_analysis(self):
        """Stop the analysis thread"""
        self.analysis_active = False
        if self.analysis_thread:
            self.analysis_thread.join()
            logger.info("Predictive intelligence analysis stopped")
    
    def _analysis_loop(self):
        """Main analysis loop"""
        while self.analysis_active:
            try:
                # Analyze usage patterns
                self._analyze_usage_patterns()
                
                # Generate build recommendations
                self._generate_build_recommendations()
                
                # Update revenue heatmap
                self._update_revenue_heatmap()
                
                # Analyze profit performance
                self._analyze_profit_performance()
                
                # Generate market insights
                self._generate_market_insights()
                
                # Feed data to LLM factory
                self._feed_data_to_llm()
                
                # Sleep for analysis interval
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
                time.sleep(60)
    
    def _analyze_usage_patterns(self):
        """Analyze usage patterns across systems, agents, and templates"""
        try:
            # Analyze system usage
            if self.system_delivery:
                self._analyze_system_usage()
            
            # Analyze agent usage
            if self.agent_ecosystem:
                self._analyze_agent_usage()
            
            # Analyze template usage
            if self.storefront:
                self._analyze_template_usage()
                
        except Exception as e:
            logger.error(f"Error analyzing usage patterns: {e}")
    
    def _analyze_system_usage(self):
        """Analyze system delivery and usage patterns"""
        # This would analyze system delivery metrics, client usage, etc.
        # For now, create sample performance data
        sample_data = PerformanceData(
            data_id=f"system_usage_{int(time.time())}",
            item_id="sample_system",
            item_type="system",
            metric_type=PerformanceMetric.USAGE_TIME,
            value=120.5,  # minutes
            timestamp=datetime.now(),
            period="daily",
            context={"deployment_type": "hosted", "client_count": 5}
        )
        
        self._save_performance_data(sample_data)
    
    def _analyze_agent_usage(self):
        """Analyze agent ecosystem usage patterns"""
        # This would analyze agent usage, composition patterns, etc.
        sample_data = PerformanceData(
            data_id=f"agent_usage_{int(time.time())}",
            item_id="sample_agent",
            item_type="agent",
            metric_type=PerformanceMetric.DOWNLOADS,
            value=25.0,
            timestamp=datetime.now(),
            period="daily",
            context={"category": "automation", "complexity": "medium"}
        )
        
        self._save_performance_data(sample_data)
    
    def _analyze_template_usage(self):
        """Analyze storefront template usage patterns"""
        # This would analyze template downloads, ratings, etc.
        sample_data = PerformanceData(
            data_id=f"template_usage_{int(time.time())}",
            item_id="sample_template",
            item_type="template",
            metric_type=PerformanceMetric.RATING,
            value=4.5,
            timestamp=datetime.now(),
            period="daily",
            context={"category": "saas", "downloads": 150}
        )
        
        self._save_performance_data(sample_data)
    
    def _save_performance_data(self, data: PerformanceData):
        """Save performance data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO performance_data 
            (data_id, item_id, item_type, metric_type, value, timestamp, period, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.data_id,
            data.item_id,
            data.item_type,
            data.metric_type.value,
            data.value,
            data.timestamp.isoformat(),
            data.period,
            json.dumps(data.context)
        ))
        
        conn.commit()
        conn.close()
    
    def _generate_build_recommendations(self):
        """Generate build recommendations based on usage patterns and market analysis"""
        try:
            # Analyze current trends
            trends = self._analyze_current_trends()
            
            # Generate recommendations based on trends
            recommendations = self._create_recommendations_from_trends(trends)
            
            # Save recommendations
            for recommendation in recommendations:
                self._save_build_recommendation(recommendation)
                
        except Exception as e:
            logger.error(f"Error generating build recommendations: {e}")
    
    def _analyze_current_trends(self) -> Dict[str, Any]:
        """Analyze current market and usage trends"""
        trends = {
            "popular_categories": ["saas", "automation", "ai"],
            "rising_demands": ["voice_ai", "data_analytics", "workflow_automation"],
            "market_gaps": ["enterprise_security", "healthcare_ai", "financial_automation"],
            "user_preferences": ["easy_deployment", "low_code", "api_integration"]
        }
        
        return trends
    
    def _create_recommendations_from_trends(self, trends: Dict[str, Any]) -> List[BuildRecommendation]:
        """Create build recommendations from trend analysis"""
        recommendations = []
        
        # Generate system build recommendations
        for category in trends["popular_categories"]:
            recommendation = BuildRecommendation(
                recommendation_id=f"rec_{int(time.time())}_{category}",
                recommendation_type=RecommendationType.SYSTEM_BUILD,
                title=f"Build {category.title()} Management System",
                description=f"Create a comprehensive {category} management system based on current market demand",
                confidence_score=0.8,
                estimated_impact="high",
                market_demand=0.85,
                development_effort="medium",
                revenue_potential=50000.0,
                tags=[category, "management", "automation"],
                categories=[category],
                reasoning=f"High demand in {category} category with strong revenue potential",
                created_at=datetime.now(),
                is_implemented=False,
                implemented_at=None
            )
            recommendations.append(recommendation)
        
        # Generate agent recommendations
        for demand in trends["rising_demands"]:
            recommendation = BuildRecommendation(
                recommendation_id=f"rec_{int(time.time())}_{demand}",
                recommendation_type=RecommendationType.AGENT_CREATION,
                title=f"Create {demand.replace('_', ' ').title()} Agent",
                description=f"Develop an intelligent agent for {demand} automation",
                confidence_score=0.7,
                estimated_impact="medium",
                market_demand=0.75,
                development_effort="low",
                revenue_potential=15000.0,
                tags=[demand, "agent", "automation"],
                categories=["agents"],
                reasoning=f"Rising demand for {demand} solutions",
                created_at=datetime.now(),
                is_implemented=False,
                implemented_at=None
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def _save_build_recommendation(self, recommendation: BuildRecommendation):
        """Save build recommendation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO build_recommendations 
            (recommendation_id, recommendation_type, title, description, confidence_score,
             estimated_impact, market_demand, development_effort, revenue_potential,
             tags, categories, reasoning, created_at, is_implemented, implemented_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recommendation.recommendation_id,
            recommendation.recommendation_type.value,
            recommendation.title,
            recommendation.description,
            recommendation.confidence_score,
            recommendation.estimated_impact,
            recommendation.market_demand,
            recommendation.development_effort,
            recommendation.revenue_potential,
            json.dumps(recommendation.tags),
            json.dumps(recommendation.categories),
            recommendation.reasoning,
            recommendation.created_at.isoformat(),
            1 if recommendation.is_implemented else 0,
            recommendation.implemented_at.isoformat() if recommendation.implemented_at else None
        ))
        
        conn.commit()
        conn.close()
    
    def _update_revenue_heatmap(self):
        """Update revenue heatmap for all items"""
        try:
            # Get all items from storefront
            if self.storefront:
                listings = self.storefront.get_all_listings()
                
                for listing in listings:
                    heatmap = self._calculate_revenue_heatmap(listing)
                    self._save_revenue_heatmap(heatmap)
                    
        except Exception as e:
            logger.error(f"Error updating revenue heatmap: {e}")
    
    def _calculate_revenue_heatmap(self, listing) -> RevenueHeatmap:
        """Calculate revenue heatmap for a listing"""
        # This would calculate actual revenue metrics
        # For now, create sample data
        return RevenueHeatmap(
            item_id=listing.listing_id,
            item_type=listing.listing_type.value,
            total_revenue=listing.price * 100,  # Sample revenue
            revenue_trend=15.5,  # 15.5% increase
            download_count=150,
            upgrade_count=25,
            user_count=75,
            average_rating=4.2,
            market_trend=MarketTrend.RISING,
            last_updated=datetime.now(),
            performance_metrics={
                "conversion_rate": 0.25,
                "retention_rate": 0.85,
                "avg_session_time": 45.5
            }
        )
    
    def _save_revenue_heatmap(self, heatmap: RevenueHeatmap):
        """Save revenue heatmap to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO revenue_heatmap 
            (item_id, item_type, total_revenue, revenue_trend, download_count,
             upgrade_count, user_count, average_rating, market_trend,
             last_updated, performance_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            heatmap.item_id,
            heatmap.item_type,
            heatmap.total_revenue,
            heatmap.revenue_trend,
            heatmap.download_count,
            heatmap.upgrade_count,
            heatmap.user_count,
            heatmap.average_rating,
            heatmap.market_trend.value,
            heatmap.last_updated.isoformat(),
            json.dumps(heatmap.performance_metrics)
        ))
        
        conn.commit()
        conn.close()
    
    def _analyze_profit_performance(self):
        """Analyze profit performance for all items"""
        try:
            # Get revenue heatmap data
            heatmaps = self._get_all_revenue_heatmaps()
            
            for heatmap in heatmaps:
                profit_analysis = self._calculate_profit_analysis(heatmap)
                self._save_profit_analysis(profit_analysis)
                
        except Exception as e:
            logger.error(f"Error analyzing profit performance: {e}")
    
    def _get_all_revenue_heatmaps(self) -> List[RevenueHeatmap]:
        """Get all revenue heatmaps"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM revenue_heatmap')
        results = cursor.fetchall()
        conn.close()
        
        heatmaps = []
        for result in results:
            item_id, item_type, total_revenue, revenue_trend, download_count, upgrade_count, user_count, average_rating, market_trend, last_updated, performance_metrics = result
            
            heatmaps.append(RevenueHeatmap(
                item_id=item_id,
                item_type=item_type,
                total_revenue=total_revenue,
                revenue_trend=revenue_trend,
                download_count=download_count,
                upgrade_count=upgrade_count,
                user_count=user_count,
                average_rating=average_rating,
                market_trend=MarketTrend(market_trend),
                last_updated=datetime.fromisoformat(last_updated),
                performance_metrics=json.loads(performance_metrics)
            ))
        
        return heatmaps
    
    def _calculate_profit_analysis(self, heatmap: RevenueHeatmap) -> ProfitAnalysis:
        """Calculate profit analysis for an item"""
        # Estimate costs based on item type and usage
        estimated_cost = self._estimate_item_cost(heatmap)
        profit_margin = ((heatmap.total_revenue - estimated_cost) / heatmap.total_revenue * 100) if heatmap.total_revenue > 0 else 0
        roi = ((heatmap.total_revenue - estimated_cost) / estimated_cost * 100) if estimated_cost > 0 else 0
        
        return ProfitAnalysis(
            item_id=heatmap.item_id,
            item_type=heatmap.item_type,
            total_revenue=heatmap.total_revenue,
            total_cost=estimated_cost,
            profit_margin=profit_margin,
            roi=roi,
            break_even_point=datetime.now() + timedelta(days=30),  # Sample
            pricing_recommendation=self._generate_pricing_recommendation(heatmap),
            bundling_suggestions=self._generate_bundling_suggestions(heatmap),
            market_position=self._analyze_market_position(heatmap),
            competitive_analysis=self._analyze_competition(heatmap)
        )
    
    def _estimate_item_cost(self, heatmap: RevenueHeatmap) -> float:
        """Estimate the cost of an item"""
        # Simple cost estimation based on item type and usage
        base_cost = 1000.0  # Base development cost
        
        if heatmap.item_type == "system":
            base_cost = 5000.0
        elif heatmap.item_type == "agent":
            base_cost = 2000.0
        elif heatmap.item_type == "template":
            base_cost = 500.0
        
        # Add operational costs
        operational_cost = heatmap.user_count * 2.0  # $2 per user per month
        
        return base_cost + operational_cost
    
    def _generate_pricing_recommendation(self, heatmap: RevenueHeatmap) -> str:
        """Generate pricing recommendation"""
        if heatmap.market_trend == MarketTrend.RISING:
            return "Consider increasing price by 10-15% due to high demand"
        elif heatmap.market_trend == MarketTrend.DECLINING:
            return "Consider reducing price or adding features to maintain competitiveness"
        else:
            return "Current pricing appears optimal for market conditions"
    
    def _generate_bundling_suggestions(self, heatmap: RevenueHeatmap) -> List[str]:
        """Generate bundling suggestions"""
        suggestions = []
        
        if heatmap.item_type == "system":
            suggestions.extend([
                "Bundle with complementary agents",
                "Offer premium support package",
                "Include training materials"
            ])
        elif heatmap.item_type == "agent":
            suggestions.extend([
                "Bundle with similar automation agents",
                "Offer customization services",
                "Include integration templates"
            ])
        
        return suggestions
    
    def _analyze_market_position(self, heatmap: RevenueHeatmap) -> str:
        """Analyze market position"""
        if heatmap.average_rating >= 4.5 and heatmap.revenue_trend > 10:
            return "Market leader with strong growth"
        elif heatmap.average_rating >= 4.0 and heatmap.revenue_trend > 0:
            return "Strong competitor with positive growth"
        elif heatmap.average_rating >= 3.5:
            return "Established player with room for improvement"
        else:
            return "Needs improvement in quality and market positioning"
    
    def _analyze_competition(self, heatmap: RevenueHeatmap) -> Dict[str, Any]:
        """Analyze competitive landscape"""
        return {
            "competitor_count": 15,  # Sample data
            "market_share": 0.08,  # 8% market share
            "competitive_advantages": ["ease_of_use", "integration_capabilities"],
            "competitive_disadvantages": ["pricing", "feature_set"],
            "recommendations": [
                "Focus on user experience improvements",
                "Expand integration options",
                "Consider competitive pricing strategy"
            ]
        }
    
    def _save_profit_analysis(self, analysis: ProfitAnalysis):
        """Save profit analysis to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO profit_analysis 
            (item_id, item_type, total_revenue, total_cost, profit_margin, roi,
             break_even_point, pricing_recommendation, bundling_suggestions,
             market_position, competitive_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            analysis.item_id,
            analysis.item_type,
            analysis.total_revenue,
            analysis.total_cost,
            analysis.profit_margin,
            analysis.roi,
            analysis.break_even_point.isoformat(),
            analysis.pricing_recommendation,
            json.dumps(analysis.bundling_suggestions),
            analysis.market_position,
            json.dumps(analysis.competitive_analysis)
        ))
        
        conn.commit()
        conn.close()
    
    def _generate_market_insights(self):
        """Generate market insights based on data analysis"""
        try:
            # Analyze performance data
            performance_data = self._get_recent_performance_data()
            
            # Generate insights
            insights = self._create_market_insights(performance_data)
            
            # Save insights
            for insight in insights:
                self._save_market_insight(insight)
                
        except Exception as e:
            logger.error(f"Error generating market insights: {e}")
    
    def _get_recent_performance_data(self) -> List[PerformanceData]:
        """Get recent performance data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM performance_data 
            WHERE timestamp > datetime('now', '-7 days')
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        data = []
        for result in results:
            data_id, item_id, item_type, metric_type, value, timestamp, period, context = result
            
            data.append(PerformanceData(
                data_id=data_id,
                item_id=item_id,
                item_type=item_type,
                metric_type=PerformanceMetric(metric_type),
                value=value,
                timestamp=datetime.fromisoformat(timestamp),
                period=period,
                context=json.loads(context)
            ))
        
        return data
    
    def _create_market_insights(self, performance_data: List[PerformanceData]) -> List[MarketInsight]:
        """Create market insights from performance data"""
        insights = []
        
        # Analyze trends by category
        categories = {}
        for data in performance_data:
            category = data.context.get("category", "general")
            if category not in categories:
                categories[category] = []
            categories[category].append(data.value)
        
        for category, values in categories.items():
            if len(values) >= 3:  # Need minimum data points
                avg_value = statistics.mean(values)
                trend = self._determine_trend(values)
                
                insight = MarketInsight(
                    insight_id=f"insight_{int(time.time())}_{category}",
                    category=category,
                    trend=trend,
                    description=f"{category.title()} category showing {trend.value} trend with average performance of {avg_value:.2f}",
                    confidence=0.7,
                    data_points=[{"value": v, "timestamp": data.timestamp.isoformat()} for data, v in zip(performance_data, values)],
                    recommendations=self._generate_insight_recommendations(category, trend),
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(days=30)
                )
                insights.append(insight)
        
        return insights
    
    def _determine_trend(self, values: List[float]) -> MarketTrend:
        """Determine trend from a series of values"""
        if len(values) < 2:
            return MarketTrend.STABLE
        
        # Simple trend analysis
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        if len(first_half) == 0 or len(second_half) == 0:
            return MarketTrend.STABLE
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        change_percent = ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
        
        if change_percent > 10:
            return MarketTrend.RISING
        elif change_percent < -10:
            return MarketTrend.DECLINING
        else:
            return MarketTrend.STABLE
    
    def _generate_insight_recommendations(self, category: str, trend: MarketTrend) -> List[str]:
        """Generate recommendations based on insight"""
        recommendations = []
        
        if trend == MarketTrend.RISING:
            recommendations.extend([
                f"Increase focus on {category} development",
                f"Consider premium pricing for {category} solutions",
                f"Expand {category} feature set"
            ])
        elif trend == MarketTrend.DECLINING:
            recommendations.extend([
                f"Reassess {category} market positioning",
                f"Consider feature improvements for {category}",
                f"Analyze competitive landscape in {category}"
            ])
        else:
            recommendations.extend([
                f"Maintain current {category} strategy",
                f"Look for incremental improvements in {category}",
                f"Monitor {category} market changes"
            ])
        
        return recommendations
    
    def _save_market_insight(self, insight: MarketInsight):
        """Save market insight to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO market_insights 
            (insight_id, category, trend, description, confidence, data_points,
             recommendations, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            insight.insight_id,
            insight.category,
            insight.trend.value,
            insight.description,
            insight.confidence,
            json.dumps(insight.data_points),
            json.dumps(insight.recommendations),
            insight.created_at.isoformat(),
            insight.expires_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _feed_data_to_llm(self):
        """Feed analysis data to LLM factory for training"""
        try:
            if not self.llm_factory:
                return
            
            # Collect training data
            training_data = self._collect_training_data()
            
            # Feed to LLM factory
            for data in training_data:
                if hasattr(self.llm_factory, 'add_training_data'):
                    self.llm_factory.add_training_data(data)
                    
        except Exception as e:
            logger.error(f"Error feeding data to LLM: {e}")
    
    def _collect_training_data(self) -> List[Dict[str, Any]]:
        """Collect training data from various sources"""
        training_data = []
        
        # Collect performance data
        performance_data = self._get_recent_performance_data()
        for data in performance_data:
            training_data.append({
                "type": "performance_analysis",
                "item_type": data.item_type,
                "metric": data.metric_type.value,
                "value": data.value,
                "context": data.context,
                "timestamp": data.timestamp.isoformat()
            })
        
        # Collect market insights
        insights = self._get_recent_market_insights()
        for insight in insights:
            training_data.append({
                "type": "market_analysis",
                "category": insight.category,
                "trend": insight.trend.value,
                "description": insight.description,
                "recommendations": insight.recommendations
            })
        
        return training_data
    
    def _get_recent_market_insights(self) -> List[MarketInsight]:
        """Get recent market insights"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM market_insights 
            WHERE created_at > datetime('now', '-7 days')
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        insights = []
        for result in results:
            insight_id, category, trend, description, confidence, data_points, recommendations, created_at, expires_at = result
            
            insights.append(MarketInsight(
                insight_id=insight_id,
                category=category,
                trend=MarketTrend(trend),
                description=description,
                confidence=confidence,
                data_points=json.loads(data_points),
                recommendations=json.loads(recommendations),
                created_at=datetime.fromisoformat(created_at),
                expires_at=datetime.fromisoformat(expires_at)
            ))
        
        return insights
    
    def record_rlhf_signal(self, user_id: str, system_id: str, interaction_type: str, 
                          user_action: str, system_response: str, user_feedback: RLHFSignal,
                          context: Dict[str, Any] = None, confidence_score: float = 1.0):
        """Record RLHF signal for training"""
        data_id = f"rlhf_{int(time.time())}_{user_id}"
        
        # Calculate training value based on feedback
        training_value = 1.0 if user_feedback == RLHFSignal.HELPFUL else 0.0
        
        rlhf_data = RLHFTrainingData(
            data_id=data_id,
            user_id=user_id,
            system_id=system_id,
            interaction_type=interaction_type,
            user_action=user_action,
            system_response=system_response,
            user_feedback=user_feedback,
            context=context or {},
            timestamp=datetime.now(),
            confidence_score=confidence_score,
            training_value=training_value
        )
        
        self._save_rlhf_data(rlhf_data)
    
    def _save_rlhf_data(self, data: RLHFTrainingData):
        """Save RLHF training data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO rlhf_training_data 
            (data_id, user_id, system_id, interaction_type, user_action,
             system_response, user_feedback, context, timestamp,
             confidence_score, training_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.data_id,
            data.user_id,
            data.system_id,
            data.interaction_type,
            data.user_action,
            data.system_response,
            data.user_feedback.value,
            json.dumps(data.context),
            data.timestamp.isoformat(),
            data.confidence_score,
            data.training_value
        ))
        
        conn.commit()
        conn.close()
    
    def get_build_recommendations(self, recommendation_type: Optional[RecommendationType] = None, 
                                limit: int = 10) -> List[BuildRecommendation]:
        """Get build recommendations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM build_recommendations WHERE is_implemented = 0"
        params = []
        
        if recommendation_type:
            query += " AND recommendation_type = ?"
            params.append(recommendation_type.value)
        
        query += " ORDER BY confidence_score DESC, revenue_potential DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        recommendations = []
        for result in results:
            recommendation_id, rec_type, title, description, confidence_score, estimated_impact, market_demand, development_effort, revenue_potential, tags, categories, reasoning, created_at, is_implemented, implemented_at = result
            
            recommendations.append(BuildRecommendation(
                recommendation_id=recommendation_id,
                recommendation_type=RecommendationType(rec_type),
                title=title,
                description=description,
                confidence_score=confidence_score,
                estimated_impact=estimated_impact,
                market_demand=market_demand,
                development_effort=development_effort,
                revenue_potential=revenue_potential,
                tags=json.loads(tags),
                categories=json.loads(categories),
                reasoning=reasoning,
                created_at=datetime.fromisoformat(created_at),
                is_implemented=bool(is_implemented),
                implemented_at=datetime.fromisoformat(implemented_at) if implemented_at else None
            ))
        
        return recommendations
    
    def get_revenue_heatmap(self, item_type: Optional[str] = None) -> List[RevenueHeatmap]:
        """Get revenue heatmap data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM revenue_heatmap"
        params = []
        
        if item_type:
            query += " WHERE item_type = ?"
            params.append(item_type)
        
        query += " ORDER BY total_revenue DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        heatmaps = []
        for result in results:
            item_id, item_type, total_revenue, revenue_trend, download_count, upgrade_count, user_count, average_rating, market_trend, last_updated, performance_metrics = result
            
            heatmaps.append(RevenueHeatmap(
                item_id=item_id,
                item_type=item_type,
                total_revenue=total_revenue,
                revenue_trend=revenue_trend,
                download_count=download_count,
                upgrade_count=upgrade_count,
                user_count=user_count,
                average_rating=average_rating,
                market_trend=MarketTrend(market_trend),
                last_updated=datetime.fromisoformat(last_updated),
                performance_metrics=json.loads(performance_metrics)
            ))
        
        return heatmaps
    
    def get_profit_analysis(self, item_id: Optional[str] = None) -> List[ProfitAnalysis]:
        """Get profit analysis data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM profit_analysis"
        params = []
        
        if item_id:
            query += " WHERE item_id = ?"
            params.append(item_id)
        
        query += " ORDER BY roi DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        analyses = []
        for result in results:
            item_id, item_type, total_revenue, total_cost, profit_margin, roi, break_even_point, pricing_recommendation, bundling_suggestions, market_position, competitive_analysis = result
            
            analyses.append(ProfitAnalysis(
                item_id=item_id,
                item_type=item_type,
                total_revenue=total_revenue,
                total_cost=total_cost,
                profit_margin=profit_margin,
                roi=roi,
                break_even_point=datetime.fromisoformat(break_even_point),
                pricing_recommendation=pricing_recommendation,
                bundling_suggestions=json.loads(bundling_suggestions),
                market_position=market_position,
                competitive_analysis=json.loads(competitive_analysis)
            ))
        
        return analyses
    
    def get_market_insights(self, category: Optional[str] = None) -> List[MarketInsight]:
        """Get market insights"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM market_insights WHERE expires_at > datetime('now')"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY confidence DESC, created_at DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        insights = []
        for result in results:
            insight_id, category, trend, description, confidence, data_points, recommendations, created_at, expires_at = result
            
            insights.append(MarketInsight(
                insight_id=insight_id,
                category=category,
                trend=MarketTrend(trend),
                description=description,
                confidence=confidence,
                data_points=json.loads(data_points),
                recommendations=json.loads(recommendations),
                created_at=datetime.fromisoformat(created_at),
                expires_at=datetime.fromisoformat(expires_at)
            ))
        
        return insights
    
    def get_predictive_statistics(self) -> Dict[str, Any]:
        """Get predictive intelligence statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total recommendations
        cursor.execute('SELECT COUNT(*) FROM build_recommendations')
        total_recommendations = cursor.fetchone()[0]
        
        # Implemented recommendations
        cursor.execute('SELECT COUNT(*) FROM build_recommendations WHERE is_implemented = 1')
        implemented_recommendations = cursor.fetchone()[0]
        
        # Total revenue
        cursor.execute('SELECT SUM(total_revenue) FROM revenue_heatmap')
        total_revenue = cursor.fetchone()[0] or 0
        
        # Average ROI
        cursor.execute('SELECT AVG(roi) FROM profit_analysis')
        avg_roi = cursor.fetchone()[0] or 0
        
        # Active market insights
        cursor.execute('SELECT COUNT(*) FROM market_insights WHERE expires_at > datetime("now")')
        active_insights = cursor.fetchone()[0]
        
        # RLHF data points
        cursor.execute('SELECT COUNT(*) FROM rlhf_training_data')
        rlhf_data_points = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_recommendations": total_recommendations,
            "implemented_recommendations": implemented_recommendations,
            "implementation_rate": (implemented_recommendations / total_recommendations * 100) if total_recommendations > 0 else 0,
            "total_revenue": total_revenue,
            "average_roi": avg_roi,
            "active_insights": active_insights,
            "rlhf_data_points": rlhf_data_points
        }
