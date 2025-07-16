"""
Web scraper for news sites without RSS feeds
"""
from typing import List, Dict, Optional
from datetime import datetime
import logging
import re
from urllib.parse import urljoin, urlparse

from .base_scraper import BaseScraper, Article

logger = logging.getLogger(__name__)


class WebScraper(BaseScraper):
    """Scraper for websites without RSS feeds"""
    
    def __init__(self, source_name: str, base_url: str, 
                 category: str, config: Dict,
                 article_selector: str = None,
                 title_selector: str = None,
                 link_selector: str = None):
        super().__init__(source_name, config)
        self.base_url = base_url
        self.category = category
        self.article_selector = article_selector or '.article'
        self.title_selector = title_selector or 'h2, h3, .title'
        self.link_selector = link_selector or 'a'
        
    def scrape_articles(self) -> List[Article]:
        """Scrape articles from website"""
        articles = []
        max_articles = self.config.get('max_articles_per_source', 10)
        
        try:
            logger.info(f"Scraping website: {self.source_name}")
            soup = self.fetch_page(self.base_url)
            
            if not soup:
                return articles
                
            # Find article containers
            article_elements = soup.select(self.article_selector)
            
            for element in article_elements[:max_articles]:
                try:
                    article = self._parse_article_element(element)
                    if article:
                        articles.append(article)
                        self.rate_limit()
                except Exception as e:
                    logger.error(f"Error parsing article from {self.source_name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping website {self.source_name}: {e}")
            
        logger.info(f"Scraped {len(articles)} articles from {self.source_name}")
        return articles
    
    def _parse_article_element(self, element) -> Optional[Article]:
        """Parse individual article element"""
        # Extract title
        title_elem = element.select_one(self.title_selector)
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)
        
        # Extract link
        link_elem = element.select_one(self.link_selector)
        if not link_elem:
            link_elem = title_elem.find('a')
        
        if not link_elem or not link_elem.get('href'):
            return None
            
        url = self.clean_url(link_elem['href'], self.base_url)
        
        # Get full article content
        body = self._fetch_article_content(url)
        if not body:
            # Fallback to element text
            body = element.get_text(strip=True)
            
        # Try to extract publication date
        published_at = self._extract_date(element)
        
        # Try to extract author
        author = self._extract_author(element)
        
        return Article(
            title=title,
            url=url,
            body=body,
            category=self.category,
            source=self.source_name,
            published_at=published_at,
            scraped_at=datetime.now(),
            author=author
        )
    
    def _fetch_article_content(self, url: str) -> str:
        """Fetch full article content"""
        try:
            soup = self.fetch_page(url)
            if soup:
                return self.extract_text_content(soup)
        except Exception as e:
            logger.debug(f"Could not fetch article content for {url}: {e}")
        return ""
    
    def _extract_date(self, element) -> Optional[datetime]:
        """Try to extract publication date from article element"""
        date_selectors = [
            'time', '.date', '.published', '.timestamp',
            '[datetime]', '.post-date'
        ]
        
        for selector in date_selectors:
            date_elem = element.select_one(selector)
            if date_elem:
                # Try datetime attribute first
                date_str = date_elem.get('datetime')
                if not date_str:
                    date_str = date_elem.get_text(strip=True)
                
                if date_str:
                    try:
                        from dateutil import parser
                        return parser.parse(date_str)
                    except:
                        continue
        return None
    
    def _extract_author(self, element) -> Optional[str]:
        """Try to extract author from article element"""
        author_selectors = [
            '.author', '.byline', '.by', '[rel="author"]'
        ]
        
        for selector in author_selectors:
            author_elem = element.select_one(selector)
            if author_elem:
                author = author_elem.get_text(strip=True)
                # Clean up author text
                author = re.sub(r'^by\s+', '', author, flags=re.IGNORECASE)
                if author:
                    return author
        return None


class HackerNewsScraper(WebScraper):
    """Specialized scraper for Hacker News"""
    
    def __init__(self, config: Dict):
        super().__init__(
            source_name="Hacker News",
            base_url="https://news.ycombinator.com/",
            category="tech",
            config=config,
            article_selector=".athing",
            title_selector=".storylink",
            link_selector=".storylink"
        )
    
    def _parse_article_element(self, element) -> Optional[Article]:
        """Custom parsing for Hacker News format"""
        title_elem = element.select_one('.storylink')
        if not title_elem:
            return None
            
        title = title_elem.get_text(strip=True)
        url = title_elem.get('href', '')
        
        # HN external links are direct, internal are relative
        if not url.startswith('http'):
            url = urljoin(self.base_url, url)
            
        # For HN, we'll use the title as body since it's a link aggregator
        body = title
        
        # Try to get additional metadata from sibling element
        article_id = element.get('id')
        if article_id:
            # Look for the subtext element that follows
            next_elem = element.find_next_sibling('tr')
            if next_elem:
                subtext = next_elem.select_one('.subtext')
                if subtext:
                    # Extract score, author, time
                    score_elem = subtext.select_one('.score')
                    author_elem = subtext.select_one('.hnuser')
                    time_elem = subtext.select_one('.age')
                    
                    author = author_elem.get_text(strip=True) if author_elem else None
                    
                    # Add metadata to body
                    metadata = []
                    if score_elem:
                        metadata.append(f"Score: {score_elem.get_text(strip=True)}")
                    if time_elem:
                        metadata.append(f"Time: {time_elem.get_text(strip=True)}")
                    
                    if metadata:
                        body += f" [{', '.join(metadata)}]"
        
        return Article(
            title=title,
            url=url,
            body=body,
            category=self.category,
            source=self.source_name,
            scraped_at=datetime.now(),
            author=author if 'author' in locals() else None
        )