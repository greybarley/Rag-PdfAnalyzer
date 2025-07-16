"""
AI-powered article categorization
"""
import os
import logging
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseCategorizer(ABC):
    """Base class for article categorizers"""
    
    @abstractmethod
    def categorize(self, text: str, categories: List[str]) -> Dict[str, float]:
        """Categorize text into given categories with confidence scores"""
        pass
    
    @abstractmethod
    def categorize_batch(self, texts: List[str], categories: List[str]) -> List[Dict[str, float]]:
        """Categorize multiple texts"""
        pass


class OpenAICategorizer(BaseCategorizer):
    """OpenAI-powered categorizer"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.client = None
        
        if self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info(f"Initialized OpenAI categorizer with model: {model}")
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")
                raise
        else:
            logger.warning("No OpenAI API key provided. Set OPENAI_API_KEY environment variable.")
    
    def categorize(self, text: str, categories: List[str]) -> Dict[str, float]:
        """Categorize text using OpenAI"""
        if not self.client:
            return self._fallback_categorize(text, categories)
        
        try:
            categories_str = ", ".join(categories)
            prompt = f"""Classify the following article into ONE of these categories: {categories_str}

Article: {text[:2000]}

Instructions:
1. Choose the MOST appropriate category from the list above
2. Return only the category name, nothing else
3. If unsure, choose the closest match

Category:"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise news article classifier. Always respond with exactly one category name from the provided list."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            predicted_category = response.choices[0].message.content.strip().lower()
            
            # Create confidence scores (simplified for OpenAI)
            scores = {cat: 0.1 for cat in categories}
            
            # Find best matching category
            best_match = None
            for cat in categories:
                if cat.lower() in predicted_category or predicted_category in cat.lower():
                    best_match = cat
                    break
            
            if best_match:
                scores[best_match] = 0.9
            else:
                # Default to first category if no match
                scores[categories[0]] = 0.5
            
            logger.debug(f"Categorized as: {predicted_category}")
            return scores
            
        except Exception as e:
            logger.error(f"Error with OpenAI categorization: {e}")
            return self._fallback_categorize(text, categories)
    
    def categorize_batch(self, texts: List[str], categories: List[str]) -> List[Dict[str, float]]:
        """Categorize multiple texts"""
        results = []
        for text in texts:
            result = self.categorize(text, categories)
            results.append(result)
        return results
    
    def _fallback_categorize(self, text: str, categories: List[str]) -> Dict[str, float]:
        """Fallback categorization using keyword matching"""
        text_lower = text.lower()
        scores = {}
        
        # Define keywords for common categories
        category_keywords = {
            'tech': ['technology', 'ai', 'software', 'computer', 'digital', 'startup', 'app'],
            'finance': ['money', 'bank', 'stock', 'investment', 'market', 'economy', 'business'],
            'health': ['health', 'medical', 'doctor', 'disease', 'treatment', 'medicine'],
            'politics': ['government', 'election', 'policy', 'president', 'congress', 'political'],
            'sports': ['sport', 'game', 'team', 'player', 'championship', 'league'],
            'science': ['research', 'study', 'scientific', 'discovery', 'experiment'],
            'entertainment': ['movie', 'music', 'celebrity', 'entertainment', 'film', 'show']
        }
        
        for category in categories:
            score = 0.1  # Base score
            keywords = category_keywords.get(category.lower(), [category.lower()])
            
            for keyword in keywords:
                if keyword in text_lower:
                    score += 0.2
            
            scores[category] = min(score, 1.0)
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return scores


class HuggingFaceCategorizer(BaseCategorizer):
    """Hugging Face zero-shot classification categorizer"""
    
    def __init__(self, model_name: str = "facebook/bart-large-mnli"):
        self.model_name = model_name
        self.classifier = None
        
        try:
            from transformers import pipeline
            self.classifier = pipeline(
                "zero-shot-classification",
                model=model_name,
                device=-1  # Use CPU by default
            )
            logger.info(f"Initialized Hugging Face categorizer with model: {model_name}")
        except ImportError:
            logger.error("Transformers package not installed. Install with: pip install transformers torch")
            raise
        except Exception as e:
            logger.error(f"Error initializing Hugging Face categorizer: {e}")
            raise
    
    def categorize(self, text: str, categories: List[str]) -> Dict[str, float]:
        """Categorize text using Hugging Face zero-shot classification"""
        if not self.classifier:
            return self._fallback_categorize(text, categories)
        
        try:
            # Limit text length for model processing
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            result = self.classifier(text, categories)
            
            # Convert to dictionary format
            scores = {}
            for label, score in zip(result['labels'], result['scores']):
                scores[label] = float(score)
            
            logger.debug(f"Categorization scores: {scores}")
            return scores
            
        except Exception as e:
            logger.error(f"Error with Hugging Face categorization: {e}")
            return self._fallback_categorize(text, categories)
    
    def categorize_batch(self, texts: List[str], categories: List[str]) -> List[Dict[str, float]]:
        """Categorize multiple texts"""
        if not self.classifier:
            return [self._fallback_categorize(text, categories) for text in texts]
        
        try:
            results = []
            for text in texts:
                result = self.categorize(text, categories)
                results.append(result)
            return results
            
        except Exception as e:
            logger.error(f"Error with batch categorization: {e}")
            return [self.categorize(text, categories) for text in texts]
    
    def _fallback_categorize(self, text: str, categories: List[str]) -> Dict[str, float]:
        """Fallback categorization using keyword matching"""
        text_lower = text.lower()
        scores = {}
        
        # Define keywords for common categories
        category_keywords = {
            'tech': ['technology', 'ai', 'software', 'computer', 'digital', 'startup', 'app'],
            'finance': ['money', 'bank', 'stock', 'investment', 'market', 'economy', 'business'],
            'health': ['health', 'medical', 'doctor', 'disease', 'treatment', 'medicine'],
            'politics': ['government', 'election', 'policy', 'president', 'congress', 'political'],
            'sports': ['sport', 'game', 'team', 'player', 'championship', 'league'],
            'science': ['research', 'study', 'scientific', 'discovery', 'experiment'],
            'entertainment': ['movie', 'music', 'celebrity', 'entertainment', 'film', 'show']
        }
        
        for category in categories:
            score = 0.1  # Base score
            keywords = category_keywords.get(category.lower(), [category.lower()])
            
            for keyword in keywords:
                if keyword in text_lower:
                    score += 0.2
            
            scores[category] = min(score, 1.0)
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return scores


class ArticleCategorizer:
    """Main article categorizer that can use different backends"""
    
    def __init__(self, backend: str = "huggingface", categories: List[str] = None, **kwargs):
        self.backend = backend
        self.categories = categories or [
            'tech', 'finance', 'health', 'politics', 
            'sports', 'entertainment', 'science', 'business'
        ]
        
        if backend == "openai":
            self.categorizer = OpenAICategorizer(**kwargs)
        elif backend == "huggingface":
            self.categorizer = HuggingFaceCategorizer(**kwargs)
        else:
            raise ValueError(f"Unknown categorizer backend: {backend}")
    
    def categorize_article(self, article_text: str, categories: List[str] = None) -> str:
        """Categorize a single article and return the best category"""
        categories = categories or self.categories
        scores = self.categorizer.categorize(article_text, categories)
        
        # Return category with highest score
        best_category = max(scores, key=scores.get)
        return best_category
    
    def categorize_articles(self, articles_text: List[str], categories: List[str] = None) -> List[str]:
        """Categorize multiple articles"""
        categories = categories or self.categories
        batch_scores = self.categorizer.categorize_batch(articles_text, categories)
        
        # Return best category for each article
        best_categories = []
        for scores in batch_scores:
            best_category = max(scores, key=scores.get)
            best_categories.append(best_category)
        
        return best_categories
    
    def categorize_with_confidence(self, article_text: str, categories: List[str] = None) -> Dict[str, float]:
        """Categorize article and return all confidence scores"""
        categories = categories or self.categories
        return self.categorizer.categorize(article_text, categories)