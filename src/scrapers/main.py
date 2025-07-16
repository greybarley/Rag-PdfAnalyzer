"""
Main news aggregator that coordinates all scrapers
"""
import yaml
import logging
from typing import List, Dict
from pathlib import Path
import concurrent.futures
from datetime import datetime

from .rss_scraper import RSSFeedScraper
from .web_scraper import WebScraper, HackerNewsScraper
from .storage import ArticleStorage
from .base_scraper import Article

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsAggregator:
    """Main news aggregation coordinator"""
    
    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.storage = ArticleStorage(
            storage_path=self.config['storage']['path']
        )
        
    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading config from {self.config_path}: {e}")
            raise
    
    def scrape_all_sources(self, parallel: bool = True) -> List[Article]:
        """Scrape articles from all enabled sources"""
        logger.info("Starting news aggregation...")
        
        all_articles = []
        scrapers = self._create_scrapers()
        
        if parallel and len(scrapers) > 1:
            # Run scrapers in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_scraper = {
                    executor.submit(self._scrape_source, scraper): scraper 
                    for scraper in scrapers
                }
                
                for future in concurrent.futures.as_completed(future_to_scraper):
                    scraper = future_to_scraper[future]
                    try:
                        articles = future.result()
                        all_articles.extend(articles)
                        
                        # Save articles for this source
                        if articles:
                            self.storage.save_articles(articles, scraper.source_name)
                            
                    except Exception as e:
                        logger.error(f"Error scraping {scraper.source_name}: {e}")
        else:
            # Run scrapers sequentially
            for scraper in scrapers:
                try:
                    articles = self._scrape_source(scraper)
                    all_articles.extend(articles)
                    
                    # Save articles for this source
                    if articles:
                        self.storage.save_articles(articles, scraper.source_name)
                        
                except Exception as e:
                    logger.error(f"Error scraping {scraper.source_name}: {e}")
        
        # Save all articles together
        if all_articles:
            self.storage.save_articles(all_articles, "all_sources")
            
        logger.info(f"Scraped {len(all_articles)} total articles from {len(scrapers)} sources")
        return all_articles
    
    def _create_scrapers(self) -> List:
        """Create scraper instances based on configuration"""
        scrapers = []
        scraping_config = self.config.get('scraping', {})
        
        # Create RSS feed scrapers
        for feed_config in self.config['news_sources']['rss_feeds']:
            if feed_config.get('enabled', True):
                scraper = RSSFeedScraper(
                    source_name=feed_config['name'],
                    feed_url=feed_config['url'],
                    category=feed_config['category'],
                    config=scraping_config
                )
                scrapers.append(scraper)
        
        # Create web scrapers
        for web_config in self.config['news_sources']['web_sources']:
            if web_config.get('enabled', False):
                if web_config['name'] == "Hacker News":
                    scraper = HackerNewsScraper(config=scraping_config)
                else:
                    scraper = WebScraper(
                        source_name=web_config['name'],
                        base_url=web_config['url'],
                        category=web_config['category'],
                        config=scraping_config,
                        article_selector=web_config.get('selector'),
                        title_selector=web_config.get('title_selector')
                    )
                scrapers.append(scraper)
        
        return scrapers
    
    def _scrape_source(self, scraper) -> List[Article]:
        """Scrape articles from a single source"""
        try:
            with scraper:
                return scraper.scrape_articles()
        except Exception as e:
            logger.error(f"Error in scraper {scraper.source_name}: {e}")
            return []
    
    def get_recent_articles(self, limit: int = 50, category: str = None) -> List[Article]:
        """Get recent articles from storage"""
        return self.storage.get_latest_articles(limit=limit, category=category)
    
    def get_articles_by_category(self) -> Dict[str, List[Article]]:
        """Get articles grouped by category"""
        articles = self.storage.load_articles()
        categorized = {}
        
        for article in articles:
            category = article.category or 'uncategorized'
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(article)
        
        # Sort articles in each category by scraped_at descending
        for category in categorized:
            categorized[category].sort(key=lambda x: x.scraped_at, reverse=True)
        
        return categorized
    
    def cleanup_old_data(self):
        """Clean up old article data"""
        max_age = self.config['storage'].get('max_age_days', 7)
        self.storage.cleanup_old_articles(max_age_days=max_age)
    
    def get_stats(self) -> Dict:
        """Get aggregation statistics"""
        stats = self.storage.get_stats()
        stats['config'] = {
            'sources_configured': len(self.config['news_sources']['rss_feeds']) + 
                                len(self.config['news_sources']['web_sources']),
            'categories': self.config['categories']
        }
        return stats


def main():
    """Command line interface for running the news aggregator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='News Aggregator')
    parser.add_argument('--config', default='config/sources.yaml',
                       help='Configuration file path')
    parser.add_argument('--parallel', action='store_true', default=True,
                       help='Run scrapers in parallel')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up old articles after scraping')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics only')
    parser.add_argument('--category', type=str,
                       help='Filter articles by category')
    parser.add_argument('--limit', type=int, default=50,
                       help='Limit number of articles to display')
    
    args = parser.parse_args()
    
    try:
        aggregator = NewsAggregator(config_path=args.config)
        
        if args.stats:
            # Just show stats
            stats = aggregator.get_stats()
            print("\n=== News Aggregation Statistics ===")
            print(f"Total articles: {stats['total_articles']}")
            print(f"Sources configured: {stats['config']['sources_configured']}")
            print("\nArticles by source:")
            for source, count in stats['sources'].items():
                print(f"  {source}: {count}")
            print("\nArticles by category:")
            for category, count in stats['categories'].items():
                print(f"  {category}: {count}")
        else:
            # Run scraping
            articles = aggregator.scrape_all_sources(parallel=args.parallel)
            
            if args.cleanup:
                aggregator.cleanup_old_data()
            
            # Display recent articles
            recent = aggregator.get_recent_articles(
                limit=args.limit, 
                category=args.category
            )
            
            print(f"\n=== Latest {len(recent)} Articles ===")
            for article in recent:
                print(f"\n[{article.category.upper()}] {article.title}")
                print(f"Source: {article.source}")
                print(f"URL: {article.url}")
                print(f"Scraped: {article.scraped_at.strftime('%Y-%m-%d %H:%M')}")
                if len(article.body) > 200:
                    print(f"Preview: {article.body[:200]}...")
                else:
                    print(f"Content: {article.body}")
                print("-" * 80)
    
    except Exception as e:
        logger.error(f"Error running news aggregator: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())