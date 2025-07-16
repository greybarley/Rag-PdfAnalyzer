"""
Main article processor combining summarization and categorization
"""
import logging
from typing import List, Dict, Optional
from pathlib import Path

from .summarizer import ArticleSummarizer
from .categorizer import ArticleCategorizer
from ..scrapers.base_scraper import Article
from ..scrapers.storage import ArticleStorage

logger = logging.getLogger(__name__)


class ArticleProcessor:
    """Main processor for article summarization and categorization"""
    
    def __init__(self, 
                 summarizer_backend: str = "huggingface",
                 categorizer_backend: str = "huggingface",
                 categories: List[str] = None,
                 **kwargs):
        
        # Initialize summarizer
        try:
            self.summarizer = ArticleSummarizer(
                backend=summarizer_backend, 
                **kwargs.get('summarizer_config', {})
            )
            logger.info(f"Initialized summarizer with backend: {summarizer_backend}")
        except Exception as e:
            logger.warning(f"Failed to initialize {summarizer_backend} summarizer: {e}")
            logger.info("Falling back to keyword-based summarization")
            self.summarizer = None
        
        # Initialize categorizer
        try:
            self.categorizer = ArticleCategorizer(
                backend=categorizer_backend,
                categories=categories,
                **kwargs.get('categorizer_config', {})
            )
            logger.info(f"Initialized categorizer with backend: {categorizer_backend}")
        except Exception as e:
            logger.warning(f"Failed to initialize {categorizer_backend} categorizer: {e}")
            logger.info("Falling back to keyword-based categorization")
            self.categorizer = ArticleCategorizer(backend="huggingface")  # Fallback
        
        self.storage = ArticleStorage()
    
    def process_article(self, article: Article, 
                       summarize: bool = True,
                       categorize: bool = True,
                       max_summary_length: int = 200) -> Article:
        """Process a single article with summarization and categorization"""
        
        processed_article = article.model_copy()
        
        try:
            # Summarization
            if summarize and self.summarizer:
                logger.debug(f"Summarizing article: {article.title[:50]}...")
                summary = self.summarizer.summarize_article(
                    article.body, 
                    max_length=max_summary_length
                )
                processed_article.summary = summary
                logger.debug(f"Generated summary: {summary[:100]}...")
            
            # Categorization
            if categorize and self.categorizer:
                logger.debug(f"Categorizing article: {article.title[:50]}...")
                
                # Use title + body for better categorization
                text_for_categorization = f"{article.title}. {article.body[:1000]}"
                
                category = self.categorizer.categorize_article(text_for_categorization)
                processed_article.category = category
                logger.debug(f"Categorized as: {category}")
            
        except Exception as e:
            logger.error(f"Error processing article {article.title[:50]}: {e}")
        
        return processed_article
    
    def process_articles(self, articles: List[Article],
                        summarize: bool = True,
                        categorize: bool = True,
                        max_summary_length: int = 200) -> List[Article]:
        """Process multiple articles"""
        
        processed_articles = []
        
        logger.info(f"Processing {len(articles)} articles...")
        
        for i, article in enumerate(articles):
            try:
                processed_article = self.process_article(
                    article, 
                    summarize=summarize,
                    categorize=categorize,
                    max_summary_length=max_summary_length
                )
                processed_articles.append(processed_article)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(articles)} articles")
                    
            except Exception as e:
                logger.error(f"Error processing article {i}: {e}")
                # Add the original article if processing fails
                processed_articles.append(article)
        
        logger.info(f"Completed processing {len(processed_articles)} articles")
        return processed_articles
    
    def process_stored_articles(self, 
                               source: str = None,
                               max_articles: int = 50,
                               summarize: bool = True,
                               categorize: bool = True) -> List[Article]:
        """Process articles from storage"""
        
        # Load articles from storage
        logger.info(f"Loading articles from storage (source: {source}, max: {max_articles})")
        articles = self.storage.load_articles(source=source)
        
        if max_articles and len(articles) > max_articles:
            articles = articles[:max_articles]
            logger.info(f"Limited to {max_articles} articles")
        
        # Process articles
        processed_articles = self.process_articles(
            articles, 
            summarize=summarize,
            categorize=categorize
        )
        
        # Save processed articles
        if processed_articles:
            self.storage.save_articles(processed_articles, f"processed_{source or 'all'}")
            logger.info(f"Saved {len(processed_articles)} processed articles")
        
        return processed_articles
    
    def get_processing_stats(self, articles: List[Article]) -> Dict:
        """Generate statistics about processed articles"""
        
        stats = {
            'total_articles': len(articles),
            'with_summaries': 0,
            'with_categories': 0,
            'categories': {},
            'avg_summary_length': 0,
            'sources': {}
        }
        
        summary_lengths = []
        
        for article in articles:
            # Count summaries
            if article.summary:
                stats['with_summaries'] += 1
                summary_lengths.append(len(article.summary))
            
            # Count categories
            if article.category:
                stats['with_categories'] += 1
                category = article.category
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            # Count sources
            source = article.source
            stats['sources'][source] = stats['sources'].get(source, 0) + 1
        
        # Calculate average summary length
        if summary_lengths:
            stats['avg_summary_length'] = sum(summary_lengths) / len(summary_lengths)
        
        return stats


def main():
    """Command line interface for article processing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Article Processor - Summarization & Categorization')
    parser.add_argument('--source', type=str, help='Filter by source name')
    parser.add_argument('--max-articles', type=int, default=20, 
                       help='Maximum number of articles to process')
    parser.add_argument('--summarizer', choices=['openai', 'huggingface'], 
                       default='huggingface', help='Summarizer backend')
    parser.add_argument('--categorizer', choices=['openai', 'huggingface'],
                       default='huggingface', help='Categorizer backend')
    parser.add_argument('--no-summarize', action='store_true',
                       help='Skip summarization')
    parser.add_argument('--no-categorize', action='store_true',
                       help='Skip categorization')
    parser.add_argument('--stats-only', action='store_true',
                       help='Show statistics only')
    parser.add_argument('--summary-length', type=int, default=200,
                       help='Maximum summary length')
    
    args = parser.parse_args()
    
    try:
        # Initialize processor
        processor = ArticleProcessor(
            summarizer_backend=args.summarizer,
            categorizer_backend=args.categorizer
        )
        
        if args.stats_only:
            # Load and show stats only
            articles = processor.storage.load_articles(source=args.source)
            if args.max_articles:
                articles = articles[:args.max_articles]
            
            stats = processor.get_processing_stats(articles)
            
            print("\n=== Article Processing Statistics ===")
            print(f"Total articles: {stats['total_articles']}")
            print(f"Articles with summaries: {stats['with_summaries']}")
            print(f"Articles with categories: {stats['with_categories']}")
            print(f"Average summary length: {stats['avg_summary_length']:.1f} chars")
            
            print("\nCategories:")
            for category, count in stats['categories'].items():
                print(f"  {category}: {count}")
            
            print("\nSources:")
            for source, count in stats['sources'].items():
                print(f"  {source}: {count}")
        else:
            # Process articles
            processed_articles = processor.process_stored_articles(
                source=args.source,
                max_articles=args.max_articles,
                summarize=not args.no_summarize,
                categorize=not args.no_categorize
            )
            
            # Show results
            print(f"\n=== Processed {len(processed_articles)} Articles ===")
            for article in processed_articles[:5]:  # Show first 5
                print(f"\n[{article.category.upper() if article.category else 'UNCATEGORIZED'}] {article.title}")
                print(f"Source: {article.source}")
                if article.summary:
                    print(f"Summary: {article.summary}")
                print("-" * 80)
            
            if len(processed_articles) > 5:
                print(f"... and {len(processed_articles) - 5} more articles")
            
            # Show stats
            stats = processor.get_processing_stats(processed_articles)
            print(f"\nProcessing completed:")
            print(f"  - {stats['with_summaries']}/{stats['total_articles']} articles summarized")
            print(f"  - {stats['with_categories']}/{stats['total_articles']} articles categorized")
    
    except Exception as e:
        logger.error(f"Error running article processor: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())