"""
AI-powered article summarization
"""
import os
import logging
from typing import List, Optional, Dict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseSummarizer(ABC):
    """Base class for article summarizers"""
    
    @abstractmethod
    def summarize(self, text: str, max_length: int = 200) -> str:
        """Summarize the given text"""
        pass
    
    @abstractmethod
    def summarize_batch(self, texts: List[str], max_length: int = 200) -> List[str]:
        """Summarize multiple texts"""
        pass


class OpenAISummarizer(BaseSummarizer):
    """OpenAI-powered summarizer"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.client = None
        
        if self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info(f"Initialized OpenAI summarizer with model: {model}")
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")
                raise
        else:
            logger.warning("No OpenAI API key provided. Set OPENAI_API_KEY environment variable.")
    
    def summarize(self, text: str, max_length: int = 200) -> str:
        """Summarize text using OpenAI"""
        if not self.client:
            return self._fallback_summarize(text, max_length)
        
        try:
            # Create a prompt for summarization
            prompt = f"""Please provide a concise summary of the following article in about {max_length} characters. 
            Focus on the key points and main takeaways:

            {text[:4000]}  # Limit input to stay within token limits
            
            Summary:"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise, informative summaries of news articles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length // 3,  # Rough estimate for token to character ratio
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            logger.debug(f"Generated summary: {summary[:50]}...")
            return summary
            
        except Exception as e:
            logger.error(f"Error with OpenAI summarization: {e}")
            return self._fallback_summarize(text, max_length)
    
    def summarize_batch(self, texts: List[str], max_length: int = 200) -> List[str]:
        """Summarize multiple texts"""
        summaries = []
        for text in texts:
            summary = self.summarize(text, max_length)
            summaries.append(summary)
        return summaries
    
    def _fallback_summarize(self, text: str, max_length: int) -> str:
        """Fallback summarization using simple text truncation"""
        sentences = text.split('. ')
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) < max_length:
                summary += sentence + ". "
            else:
                break
        return summary.strip()


class HuggingFaceSummarizer(BaseSummarizer):
    """Hugging Face transformers summarizer"""
    
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        self.model_name = model_name
        self.summarizer = None
        
        try:
            from transformers import pipeline
            self.summarizer = pipeline(
                "summarization", 
                model=model_name,
                device=-1  # Use CPU by default
            )
            logger.info(f"Initialized Hugging Face summarizer with model: {model_name}")
        except ImportError:
            logger.error("Transformers package not installed. Install with: pip install transformers torch")
            raise
        except Exception as e:
            logger.error(f"Error initializing Hugging Face summarizer: {e}")
            raise
    
    def summarize(self, text: str, max_length: int = 200) -> str:
        """Summarize text using Hugging Face model"""
        if not self.summarizer:
            return self._fallback_summarize(text, max_length)
        
        try:
            # BART has input length limits
            max_input_length = 1024
            if len(text) > max_input_length:
                text = text[:max_input_length]
            
            # Calculate token-based lengths (approximate)
            max_length_tokens = max_length // 4  # Rough estimate
            min_length_tokens = max(20, max_length_tokens // 3)
            
            result = self.summarizer(
                text,
                max_length=max_length_tokens,
                min_length=min_length_tokens,
                do_sample=False
            )
            
            summary = result[0]['summary_text']
            logger.debug(f"Generated summary: {summary[:50]}...")
            return summary
            
        except Exception as e:
            logger.error(f"Error with Hugging Face summarization: {e}")
            return self._fallback_summarize(text, max_length)
    
    def summarize_batch(self, texts: List[str], max_length: int = 200) -> List[str]:
        """Summarize multiple texts"""
        if not self.summarizer:
            return [self._fallback_summarize(text, max_length) for text in texts]
        
        try:
            # Process in batches for efficiency
            max_input_length = 1024
            processed_texts = [text[:max_input_length] for text in texts]
            
            max_length_tokens = max_length // 4
            min_length_tokens = max(20, max_length_tokens // 3)
            
            results = self.summarizer(
                processed_texts,
                max_length=max_length_tokens,
                min_length=min_length_tokens,
                do_sample=False
            )
            
            return [result['summary_text'] for result in results]
            
        except Exception as e:
            logger.error(f"Error with batch summarization: {e}")
            return [self.summarize(text, max_length) for text in texts]
    
    def _fallback_summarize(self, text: str, max_length: int) -> str:
        """Fallback summarization using simple text truncation"""
        sentences = text.split('. ')
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) < max_length:
                summary += sentence + ". "
            else:
                break
        return summary.strip()


class ArticleSummarizer:
    """Main article summarizer that can use different backends"""
    
    def __init__(self, backend: str = "openai", **kwargs):
        self.backend = backend
        
        if backend == "openai":
            self.summarizer = OpenAISummarizer(**kwargs)
        elif backend == "huggingface":
            self.summarizer = HuggingFaceSummarizer(**kwargs)
        else:
            raise ValueError(f"Unknown summarizer backend: {backend}")
    
    def summarize_article(self, article_text: str, max_length: int = 200) -> str:
        """Summarize a single article"""
        return self.summarizer.summarize(article_text, max_length)
    
    def summarize_articles(self, articles_text: List[str], max_length: int = 200) -> List[str]:
        """Summarize multiple articles"""
        return self.summarizer.summarize_batch(articles_text, max_length)