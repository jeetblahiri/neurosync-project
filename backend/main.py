import os
import logging
import requests
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import arxiv
from duckduckgo_search import DDGS

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
API_KEY = os.getenv("LLM_API_KEY", "").strip()

if not API_KEY:
    logger.error("CRITICAL: LLM_API_KEY is missing from environment variables.")
else:
    logger.info(f"API Key loaded. Length: {len(API_KEY)}")

app = FastAPI(title="NeuroSync Cortex")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
class Article(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    author: Optional[str] = None
    date: str
    type: str 
    url: str

class FeedResponse(BaseModel):
    synthesis: str
    timestamp: str
    articles: List[Article]

# --- CACHE ---
cache = {
    "data": None,
    "last_updated": None
}

# --- HELPER: DYNAMIC MODEL FINDER ---
def get_best_available_model(api_key):
    """
    Asks Google which models are actually available to this Key
    and returns the best one for text generation.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to list models: {response.text}")
            return "gemini-1.5-flash" # Fallback

        data = response.json()
        models = data.get('models', [])
        
        # Priority list of models we want
        priorities = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro', 'gemini-1.0-pro']
        
        # 1. Try to find exact matches from our priority list
        for p in priorities:
            for m in models:
                # API returns names like "models/gemini-1.5-flash-001"
                if p in m['name'] and 'generateContent' in m['supportedGenerationMethods']:
                    logger.info(f"Selected Model via Discovery: {m['name']}")
                    return m['name'].replace("models/", "")

        # 2. If no priority match, grab ANY model that supports generation
        for m in models:
            if 'generateContent' in m['supportedGenerationMethods']:
                return m['name'].replace("models/", "")
                
        return "gemini-1.5-flash"
    except Exception as e:
        logger.error(f"Model discovery failed: {e}")
        return "gemini-1.5-flash"

# --- FETCHING LOGIC ---
def fetch_arxiv_papers(limit=30) -> List[Article]:
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query='(cat:q-bio.NC OR cat:cs.HC) AND ("brain computer interface" OR "neurofeedback" OR "neural link")',
            max_results=limit,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        results = []
        for r in client.results(search):
            try:
                results.append(Article(
                    id=r.entry_id.split('/')[-1],
                    title=r.title.replace('\n', ' '),
                    summary=r.summary.replace('\n', ' ')[:300] + "...",
                    source="arXiv",
                    author=r.authors[0].name if r.authors else "Unknown",
                    date=r.published.strftime("%Y-%m-%d"),
                    type="paper",
                    url=r.pdf_url
                ))
            except Exception:
                continue
        return results
    except Exception as e:
        logger.error(f"arXiv Fetch Error: {e}")
        return []

def fetch_web_news(limit=20) -> List[Article]:
    results = []
    keywords = ["Brain Computer Interface News", "Neuralink Updates", "Non-invasive BCI"]
    try:
        with DDGS() as ddgs:
            for keyword in keywords:
                news_items = list(ddgs.news(keyword, max_results=5))
                for item in news_items:
                    results.append(Article(
                        id=f"news-{len(results)}",
                        title=item['title'],
                        summary=item['body'][:300] + "...",
                        source=item['source'],
                        author="Industry Press",
                        date=datetime.now().strftime("%Y-%m-%d"),
                        type="news",
                        url=item['url']
                    ))
                    if len(results) >= limit: break
                if len(results) >= limit: break
    except Exception:
        # Silently fail on news if DDG blocks us, not critical
        return []
    return results

def generate_synthesis_raw_http(articles: List[Article]):
    """
    Uses Raw HTTP Request to bypass Python SDK issues.
    """
    if not API_KEY:
        return "Synthesis Offline: API Key missing."

    titles = "\n".join([f"- {a.title}" for a in articles[:30]])
    prompt = f"""
    You are a research assistant for a neurotechnology lab.
    Here is a list of the latest scientific papers and industry news regarding Brain-Computer Interfaces (BCI) and Neurofeedback:
    {titles}
    
    TASK: Synthesize these titles into a comprehensive two-paragraph overview. 
    - Paragraph 1: Focus on the academic research trends (new methods, algorithms, or clinical applications found in the papers).
    - Paragraph 2: Focus on the industry news and broader implications (hardware updates, startups, or societal impact).
    
    Write in a professional, clear, and informative tone suitable for a scientist. Avoid sci-fi jargon.
    """

    # 1. Find a valid model name
    model_name = get_best_available_model(API_KEY)
    
    # 2. Construct URL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
    
    # 3. Payload
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            data = response.json()
            try:
                return data['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError):
                return "Neural signal weak: AI returned empty response."
        else:
            logger.error(f"Gemini API Error {response.status_code}: {response.text}")
            return f"Neural uplink error: {response.status_code}. Raw signal rejected."
            
    except Exception as e:
        logger.error(f"HTTP Request failed: {e}")
        return "Neural uplink critical failure."

# --- ENDPOINTS ---
@app.get("/")
def health_check():
    return {"status": "online", "system": "NeuroSync Cortex"}

@app.get("/feed", response_model=FeedResponse)
async def get_feed(background_tasks: BackgroundTasks):
    global cache
    
    # Simple cache check (30 mins)
    now = datetime.now()
    if cache["data"] and cache["last_updated"] and (now - cache["last_updated"] < timedelta(minutes=30)):
        return cache["data"]
    
    # Fetch Data
    papers = fetch_arxiv_papers()
    news = fetch_web_news()
    all_raw = papers + news
    
    # Generate Synthesis (Synchronous but fast via HTTP)
    synthesis = generate_synthesis_raw_http(all_raw)
    
    response = FeedResponse(
        synthesis=synthesis,
        timestamp=now.isoformat(),
        articles=all_raw[:50]
    )
    
    cache["data"] = response
    cache["last_updated"] = now
    
    return response