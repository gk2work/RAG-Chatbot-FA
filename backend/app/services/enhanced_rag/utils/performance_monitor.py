"""
Performance monitor for Enhanced RAG Service
"""

import logging
import time
from typing import Dict, Any
from ..base.interfaces import BaseRAGComponent


class PerformanceMonitor(BaseRAGComponent):
    """Monitors and tracks performance metrics for Enhanced RAG Service"""
    
    def __init__(self):
        super().__init__()
        self.stats = {
            'total_queries': 0,
            'questions_answered': 0,
            'questions_asked': 0,
            'leads_created': 0,
            'leads_updated': 0,
            'cache_hits': 0,
            'vector_searches': 0,
            'keyword_searches': 0,
            'greeting_responses': 0,
            'detailed_responses': 0,
            'dynamic_acknowledgments': 0
        }
        self.start_time = time.time()
    
    def update_stats(self, stat_name: str, increment: int = 1):
        """Update service statistics"""
        try:
            if stat_name in self.stats:
                self.stats[stat_name] += increment
            else:
                self.stats[stat_name] = increment
        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""
        try:
            uptime_seconds = time.time() - self.start_time
            uptime_hours = uptime_seconds / 3600
            
            return {
                "service_info": {
                    "name": "Enhanced RAG Service",
                    "version": "2.0",
                    "uptime_hours": round(uptime_hours, 2),
                    "capabilities": {
                        "vector_search": True,  # Will be updated by orchestrator
                        "conversational_memory": True,
                        "lead_management": True,
                        "dynamic_questioning": True,
                        "cost_optimization": True,
                        "response_caching": True
                    }
                },
                "performance_metrics": {
                    "total_queries": self.stats.get('total_queries', 0),
                    "cache_hits": self.stats.get('cache_hits', 0),
                    "cache_hit_rate": self._calculate_cache_hit_rate(),
                    "avg_queries_per_hour": self._calculate_queries_per_hour(uptime_hours),
                    "leads_conversion_rate": self._calculate_lead_conversion_rate()
                },
                "feature_usage": {
                    "questions_answered": self.stats.get('questions_answered', 0),
                    "dynamic_questions_asked": self.stats.get('questions_asked', 0),
                    "leads_created": self.stats.get('leads_created', 0),
                    "vector_searches": self.stats.get('vector_searches', 0),
                    "keyword_searches": self.stats.get('keyword_searches', 0)
                },
                "response_types": {
                    "greeting_responses": self.stats.get('greeting_responses', 0),
                    "detailed_responses": self.stats.get('detailed_responses', 0),
                    "dynamic_acknowledgments": self.stats.get('dynamic_acknowledgments', 0)
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting service metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        try:
            total_queries = self.stats.get('total_queries', 0)
            cache_hits = self.stats.get('cache_hits', 0)
            return (cache_hits / total_queries * 100) if total_queries > 0 else 0.0
        except Exception as e:
            self.logger.error(f"Error calculating cache hit rate: {e}")
            return 0.0
    
    def _calculate_queries_per_hour(self, uptime_hours: float) -> float:
        """Calculate average queries per hour"""
        try:
            total_queries = self.stats.get('total_queries', 0)
            return total_queries / uptime_hours if uptime_hours > 0 else 0.0
        except Exception as e:
            self.logger.error(f"Error calculating queries per hour: {e}")
            return 0.0
    
    def _calculate_lead_conversion_rate(self) -> float:
        """Calculate lead conversion rate percentage"""
        try:
            total_queries = self.stats.get('total_queries', 0)
            leads_created = self.stats.get('leads_created', 0)
            return (leads_created / total_queries * 100) if total_queries > 0 else 0.0
        except Exception as e:
            self.logger.error(f"Error calculating lead conversion rate: {e}")
            return 0.0
    
    def get_rag_stats(self, university_x_id: str = None) -> Dict[str, Any]:
        """Get RAG service statistics for analytics"""
        try:
            # Basic service stats
            service_stats = {
                "service_info": {
                    "vector_search_available": True,  # Will be updated by orchestrator
                    "main_model": "gpt-4o",  # Will be updated by orchestrator
                    "extraction_model": "gpt-3.5-turbo",  # Will be updated by orchestrator
                    "cache_enabled": True,  # Will be updated by orchestrator
                    "smart_filtering_enabled": True  # Will be updated by orchestrator
                },
                "usage_stats": self.stats.copy(),
                "performance_metrics": {
                    "cache_hit_rate": self._calculate_cache_hit_rate(),
                    "active_sessions": 0,  # Will be updated by orchestrator
                    "cache_size": 0  # Will be updated by orchestrator
                }
            }
            
            # University-specific stats if X-ID provided
            if university_x_id:
                university_stats = self._get_university_specific_stats(university_x_id)
                service_stats["university_stats"] = university_stats
            
            return service_stats
            
        except Exception as e:
            self.logger.error(f"Error getting RAG stats: {e}")
            return {"error": str(e)}
    
    def _get_university_specific_stats(self, university_x_id: str) -> Dict[str, Any]:
        """Get university-specific statistics"""
        try:
            # This would be implemented to get university-specific metrics
            # For now, return basic structure
            return {
                "university_x_id": university_x_id,
                "queries_processed": self.stats.get('total_queries', 0),
                "leads_generated": self.stats.get('leads_created', 0),
                "avg_response_quality": "high",  # Would be calculated based on feedback
                "popular_queries": []  # Would track most common question types
            }
        except Exception as e:
            self.logger.error(f"Error getting university stats: {e}")
            return {"error": str(e)}
    
    def optimize_performance(self):
        """Optimize service performance"""
        try:
            self.logger.info("Performance optimization triggered")
            # This would implement performance optimization logic
            # For now, just log the event
        except Exception as e:
            self.logger.error(f"Error optimizing performance: {e}")
    
    def reset_stats(self):
        """Reset all statistics"""
        try:
            self.stats = {key: 0 for key in self.stats.keys()}
            self.start_time = time.time()
            self.logger.info("Performance statistics reset")
        except Exception as e:
            self.logger.error(f"Error resetting stats: {e}")
    
    def health_check(self) -> tuple[bool, str]:
        """Check performance monitor health"""
        try:
            # Test basic functionality
            self.update_stats('test_stat', 1)
            if self.stats.get('test_stat') == 1:
                # Clean up test stat
                del self.stats['test_stat']
                return True, "Performance monitor is healthy"
            else:
                return False, "Performance monitor failed stats update"
        except Exception as e:
            return False, f"Performance monitor health check failed: {e}"
