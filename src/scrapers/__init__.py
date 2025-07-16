"""
News scrapers package
"""
from .base_scraper import Article, BaseScraper
from .rss_scraper import RSSFeedScraper
from .web_scraper import WebScraper, HackerNewsScraper
from .storage import ArticleStorage
from .main import NewsAggregator

__all__ = [
    'Article',
    'BaseScraper', 
    'RSSFeedScraper',
    'WebScraper',
    'HackerNewsScraper',
    'ArticleStorage',
    'NewsAggregator'
]