"""
RSS Feed scraper for news sources
"""
import feedparser
from typing import List, Dict
from datetime import datetime
from dateutil import parser as date_parser
import logging

from .base_scraper import BaseScraper, Article

logger = logging.getLogger(__name__)


class RSSFeedScraper(BaseScraper):
    """Scraper for RSS/Atom feeds"""
    
    def __init__(self, source_name: str, feed_url: str, 
                 category: str, config: Dict):
        super().__init__(source_name, config)
        self.feed_url = feed_url
        self.category = category
        
    def scrape_articles(self) -> List[Article]:
        """Scrape articles from RSS feed"""
        articles = []
        max_articles = self.config.get('max_articles_per_source', 10)
        
        try:
            logger.info(f"Scraping RSS feed: {self.source_name}")
            feed = feedparser.parse(self.feed_url)
            
            if feed.bozo:
                logger.warning(f"RSS feed may have parsing issues: {self.source_name}")
            
            for entry in feed.entries[:max_articles]:
                try:
                    article = self._parse_entry(entry)
                    if article:
                        articles.append(article)
                        self.rate_limit()
                except Exception as e:
                    logger.error(f"Error parsing entry from {self.source_name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping RSS feed {self.source_name}: {e}")
            
        logger.info(f"Scraped {len(articles)} articles from {self.source_name}")
        return articles
    
    def _parse_entry(self, entry) -> Article:
        """Parse individual RSS entry"""
        # Extract title
        title = getattr(entry, 'title', '').strip()
        if not title:
            return None
            
        # Extract URL
        url = getattr(entry, 'link', '').strip()
        if not url:
            return None
            
        # Extract published date
        published_at = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published_at = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'published'):
            try:
                published_at = date_parser.parse(entry.published)
            except:
                pass
                
        # Extract author
        author = getattr(entry, 'author', None)
        
        # Extract summary/description
        summary = getattr(entry, 'summary', '').strip()
        if not summary:
            summary = getattr(entry, 'description', '').strip()
            
        # Try to get full content
        body = summary
        if hasattr(entry, 'content') and entry.content:
            # Some feeds provide full content
            if isinstance(entry.content, list) and entry.content:
                body = entry.content[0].get('value', summary)
            else:
                body = str(entry.content)
        elif url:
            # Fetch full article content
            body = self._fetch_full_content(url) or summary
            
        # Clean up HTML tags from body
        body = self._clean_html(body)
        
        # Extract tags
        tags = []
        if hasattr(entry, 'tags'):
            tags = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
            
        return Article(
            title=title,
            url=url,
            body=body,
            summary=summary,
            category=self.category,
            source=self.source_name,
            published_at=published_at,
            scraped_at=datetime.now(),
            author=author,
            tags=tags
        )
    
    def _fetch_full_content(self, url: str) -> str:
        """Fetch full article content from URL"""
        try:
            soup = self.fetch_page(url)
            if soup:
                return self.extract_text_content(soup)
        except Exception as e:
            logger.debug(f"Could not fetch full content for {url}: {e}")
        return None
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        from bs4 import BeautifulSoup
        if '<' in text and '>' in text:
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
        return ' '.join(text.split())  # Normalize whitespace