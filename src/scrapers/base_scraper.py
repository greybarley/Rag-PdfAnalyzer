"""
Base scraper class for news sources
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import logging
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Article(BaseModel):
    """Article data model"""
    title: str
    url: str
    body: str
    summary: Optional[str] = None
    category: Optional[str] = None
    source: str
    published_at: Optional[datetime] = None
    scraped_at: datetime
    author: Optional[str] = None
    tags: List[str] = []


class BaseScraper(ABC):
    """Base class for all news scrapers"""
    
    def __init__(self, source_name: str, config: Dict):
        self.source_name = source_name
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.get('user_agent', 'NewsAggregator/1.0')
        })
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        
    @abstractmethod
    def scrape_articles(self) -> List[Article]:
        """Scrape articles from the news source"""
        pass
    
    def fetch_page(self, url: str, timeout: int = 30) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_text_content(self, soup: BeautifulSoup, 
                           selectors: List[str] = None) -> str:
        """Extract main text content from article"""
        if selectors is None:
            selectors = [
                'article', '.article-content', '.post-content',
                '.entry-content', '.content', 'main'
            ]
        
        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                # Remove script and style elements
                for script in content(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                return content.get_text(strip=True, separator=' ')
        
        # Fallback to body text
        return soup.get_text(strip=True, separator=' ')
    
    def rate_limit(self):
        """Apply rate limiting between requests"""
        delay = self.config.get('delay_between_requests', 1)
        time.sleep(delay)
    
    def clean_url(self, url: str, base_url: str = None) -> str:
        """Clean and normalize URLs"""
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/') and base_url:
            url = base_url.rstrip('/') + url
        elif not url.startswith(('http://', 'https://')) and base_url:
            url = base_url.rstrip('/') + '/' + url.lstrip('/')
        return url