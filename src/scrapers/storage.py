"""
Storage system for scraped articles
"""
import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

from .base_scraper import Article

logger = logging.getLogger(__name__)


class ArticleStorage:
    """Handle storage and retrieval of articles"""
    
    def __init__(self, storage_path: str = "data/articles/"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def save_articles(self, articles: List[Article], source_name: str = None) -> str:
        """Save articles to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if source_name:
            filename = f"{source_name}_{timestamp}.json"
        else:
            filename = f"articles_{timestamp}.json"
            
        filepath = self.storage_path / filename
        
        # Convert articles to dict format
        articles_data = []
        for article in articles:
            article_dict = article.model_dump()
            # Convert datetime objects to ISO format strings
            for key, value in article_dict.items():
                if isinstance(value, datetime):
                    article_dict[key] = value.isoformat()
            articles_data.append(article_dict)
        
        # Save to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'scraped_at': datetime.now().isoformat(),
                    'source': source_name,
                    'count': len(articles),
                    'articles': articles_data
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(articles)} articles to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving articles to {filepath}: {e}")
            raise
    
    def load_articles(self, filepath: str = None, 
                     source: str = None,
                     max_age_days: int = 7) -> List[Article]:
        """Load articles from JSON file(s)"""
        articles = []
        
        if filepath:
            # Load specific file
            articles.extend(self._load_file(filepath))
        else:
            # Load all recent files
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            for json_file in self.storage_path.glob("*.json"):
                # Check file modification time
                if datetime.fromtimestamp(json_file.stat().st_mtime) < cutoff_date:
                    continue
                
                # Filter by source if specified
                if source and source not in json_file.name:
                    continue
                    
                articles.extend(self._load_file(json_file))
        
        return articles
    
    def _load_file(self, filepath: Path) -> List[Article]:
        """Load articles from a single JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            articles = []
            for article_data in data.get('articles', []):
                # Convert ISO strings back to datetime
                for key, value in article_data.items():
                    if key.endswith('_at') and isinstance(value, str):
                        try:
                            article_data[key] = datetime.fromisoformat(value)
                        except:
                            article_data[key] = None
                
                articles.append(Article(**article_data))
            
            return articles
            
        except Exception as e:
            logger.error(f"Error loading articles from {filepath}: {e}")
            return []
    
    def get_latest_articles(self, limit: int = 50, 
                          category: str = None) -> List[Article]:
        """Get latest articles, optionally filtered by category"""
        articles = self.load_articles()
        
        # Filter by category if specified
        if category:
            articles = [a for a in articles if a.category == category]
        
        # Sort by scraped_at descending
        articles.sort(key=lambda x: x.scraped_at, reverse=True)
        
        return articles[:limit]
    
    def cleanup_old_articles(self, max_age_days: int = 7):
        """Remove article files older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        removed_count = 0
        
        for json_file in self.storage_path.glob("*.json"):
            if datetime.fromtimestamp(json_file.stat().st_mtime) < cutoff_date:
                try:
                    json_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed old article file: {json_file}")
                except Exception as e:
                    logger.error(f"Error removing {json_file}: {e}")
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old article files")
    
    def get_stats(self) -> Dict:
        """Get statistics about stored articles"""
        articles = self.load_articles()
        
        stats = {
            'total_articles': len(articles),
            'sources': {},
            'categories': {},
            'date_range': {}
        }
        
        if articles:
            # Count by source
            for article in articles:
                source = article.source
                stats['sources'][source] = stats['sources'].get(source, 0) + 1
                
                if article.category:
                    category = article.category
                    stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            # Date range
            dates = [a.scraped_at for a in articles if a.scraped_at]
            if dates:
                stats['date_range'] = {
                    'earliest': min(dates).isoformat(),
                    'latest': max(dates).isoformat()
                }
        
        return stats