"""
Cache manager for Enhanced RAG Service
"""

import hashlib
import logging
import time
from typing import Dict, Any, Optional
from ..base.interfaces import BaseRAGComponent


class CacheManager(BaseRAGComponent):
    """Manages response caching for Enhanced RAG Service"""
    
    def __init__(self, enable_cache: bool = True, cache_ttl: int = 3600):
        super().__init__()
        self.enable_response_cache = enable_cache
        self.cache_ttl = cache_ttl  # 1 hour default
        self.response_cache = {}
        self.stats = {'cache_hits': 0, 'cache_misses': 0}
    
    def get_cache_key(self, question: str, university_id: str, context_summary: str) -> str:
        """Generate cache key for response caching"""
        try:
            key_data = f"{question}_{university_id}_{context_summary}"
            return hashlib.md5(key_data.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Error generating cache key: {e}")
            return f"fallback_{int(time.time())}"

    def get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if available"""
        try:
            if not self.enable_response_cache:
                return None
                
            if cache_key in self.response_cache:
                cached_item = self.response_cache[cache_key]
                if time.time() - cached_item['timestamp'] < self.cache_ttl:
                    self.stats['cache_hits'] += 1
                    self.logger.debug(f"Cache hit for key: {cache_key[:10]}...")
                    return cached_item['response']
                else:
                    del self.response_cache[cache_key]
                    self.logger.debug(f"Cache expired for key: {cache_key[:10]}...")
                    
            self.stats['cache_misses'] += 1
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving cached response: {e}")
            return None

    def cache_response(self, cache_key: str, response: Dict[str, Any]):
        """Cache response for future use with enhanced cleanup"""
        try:
            if not self.enable_response_cache:
                return
                
            self.response_cache[cache_key] = {
                'response': response,
                'timestamp': time.time()
            }
            
            # Enhanced cache cleanup - more efficient
            if len(self.response_cache) > 100:
                # Remove oldest entries more efficiently
                sorted_cache = sorted(
                    self.response_cache.items(), 
                    key=lambda x: x[1]['timestamp']
                )
                # Keep only the 50 most recent entries
                self.response_cache = dict(sorted_cache[-50:])
                self.logger.debug("Cache cleanup performed - kept 50 most recent entries")
                
        except Exception as e:
            self.logger.error(f"Error caching response: {e}")
    
    def clear_cache(self):
        """Clear all cached responses"""
        try:
            self.response_cache.clear()
            self.logger.info("Response cache cleared")
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
            hit_rate = (self.stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'enabled': self.enable_response_cache,
                'size': len(self.response_cache),
                'hits': self.stats['cache_hits'],
                'misses': self.stats['cache_misses'],
                'hit_rate_percentage': round(hit_rate, 2),
                'ttl_seconds': self.cache_ttl
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def optimize_cache(self):
        """Optimize cache performance"""
        try:
            # Remove expired entries
            current_time = time.time()
            expired_keys = [
                key for key, value in self.response_cache.items()
                if current_time - value['timestamp'] > self.cache_ttl
            ]
            
            for key in expired_keys:
                del self.response_cache[key]
            
            if expired_keys:
                self.logger.info(f"Removed {len(expired_keys)} expired cache entries")
                
        except Exception as e:
            self.logger.error(f"Error optimizing cache: {e}")
    
    def health_check(self) -> tuple[bool, str]:
        """Check cache manager health"""
        try:
            # Test basic cache operations
            test_key = "test_key"
            test_response = {"test": "data"}
            
            self.cache_response(test_key, test_response)
            cached = self.get_cached_response(test_key)
            
            if cached and cached.get("test") == "data":
                # Clean up test entry
                if test_key in self.response_cache:
                    del self.response_cache[test_key]
                return True, "Cache manager is healthy"
            else:
                return False, "Cache manager failed basic operations"
        except Exception as e:
            return False, f"Cache manager health check failed: {e}"
