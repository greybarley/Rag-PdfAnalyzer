# News Aggregator & Newsletter Generator

A comprehensive news aggregation system that scrapes articles from multiple sources, summarizes and categorizes them using AI, and generates automated newsletters.

## Features

- **Phase 1**: News scraping from multiple sources with structured storage
- **Phase 2**: AI-powered summarization and categorization
- **Phase 3**: HTML newsletter generation with templating
- **Phase 4**: Automated delivery via email and web hosting
- **Phase 5**: Streamlit UI and deployment

## Project Structure

```
├── src/
│   ├── scrapers/          # News source scrapers
│   ├── processors/        # AI summarization and categorization
│   ├── generators/        # Newsletter HTML generation
│   ├── delivery/          # Email and scheduling systems
│   └── ui/               # Streamlit frontend
├── data/                 # Scraped articles and processed data
├── templates/            # HTML newsletter templates
├── config/              # Configuration files
└── tests/               # Unit tests
```

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Configure news sources in `config/sources.yaml`
3. Run scraper: `python src/scrapers/main.py`
4. Generate newsletter: `python src/generators/newsletter.py`

## Tech Stack

- **Scraping**: BeautifulSoup, Requests, Feedparser
- **AI**: OpenAI API / Hugging Face Transformers
- **Frontend**: Streamlit
- **Delivery**: SendGrid API
- **Storage**: JSON files / SQLite
- **Deployment**: Render / HuggingFace Spaces

## Development Phases

- [x] Phase 1: Basic Pipeline (Week 1)
- [ ] Phase 2: Summarization & Categorization (Week 2)
- [ ] Phase 3: Newsletter Generator (Week 3)
- [ ] Phase 4: Delivery System (Week 4)
- [ ] Phase 5: UI & Deployment (Week 5)
