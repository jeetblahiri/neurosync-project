import os
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import arxiv
from duckduckgo_search import DDGS
import uvicorn
import openai # Assumes standard OpenAI-compatible SDK (works for DeepSeek, Groq, etc.)

# --- CONFIGURATION ---
# In production, set these via Environment Variables
API_KEY = os.getenv("LLM_API_KEY", "") # OpenAI, Gemini, or Groq API Key
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o") # or "gemini-1.5-pro"

app = FastAPI(title="NeuroSync Cortex")

# Enable CORS for your React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your frontend domain
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
    type: str # 'paper' or 'news'
    url: str

class FeedResponse(BaseModel):
    synthesis: str
    timestamp: str
    articles: List[Article]

# --- IN-MEMORY CACHE ---
# We cache results to avoid hitting APIs on every page refresh
# In a real app, use Redis.
cache = {
    "data": None,
    "last_updated": None
}

# --- FETCHING LOGIC ---

def fetch_arxiv_papers(limit=30) -> List[Article]:
    """Fetches latest BCI and Neurofeedback papers."""
    client = arxiv.Client()
    search = arxiv.Search(
        query='(cat:q-bio.NC OR cat:cs.HC) AND ("brain computer interface" OR "neurofeedback" OR "neural link")',
        max_results=limit,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    results = []
    for r in client.results(search):
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
    return results

def fetch_web_news(limit=30) -> List[Article]:
    """Uses DuckDuckGo to find latest industry news without paid APIs."""
    results = []
    keywords = ["Brain Computer Interface News", "Neuralink Competitor Updates", "Neurofeedback Technology 2025"]
    
    try:
        with DDGS() as ddgs:
            for keyword in keywords:
                # search news
                news_items = list(ddgs.news(keyword, max_results=10))
                for item in news_items:
                    results.append(Article(
                        id=f"news-{len(results)}",
                        title=item['title'],
                        summary=item['body'][:300] + "...",
                        source=item['source'],
                        author="Industry Press",
                        date=datetime.now().strftime("%Y-%m-%d"), # DDG dates vary, defaulting to now for demo
                        type="news",
                        url=item['url']
                    ))
                    if len(results) >= limit: break
                if len(results) >= limit: break
    except Exception as e:
        print(f"News fetch error: {e}")
        # Fallback if search fails
        return []
        
    return results

async def llm_curation(articles: List[Article]) -> tuple[List[Article], str]:
    """
    Uses an LLM to:
    1. Select the 50 most relevant/impactful items.
    2. Write the synthesis paragraph.
    """
    if not API_KEY:
        # Fallback if no API key is present
        print("No LLM API Key provided. Returning raw list.")
        synthesis = f"Automated aggregation of {len(articles)} sources. Key trends suggest focus on non-invasive modalities and AI integration."
        return articles[:50], synthesis

    # Prepare prompt
    titles = "\n".join([f"- [{a.type}] {a.title}" for a in articles])
    
    prompt = f"""
    You are the "Cortex" of a BCI research dashboard. 
    Here is a list of raw data inputs (papers and news) fetched from the internet:
    
    {titles}
    
    TASK 1: Write a high-level, sci-fi style "Daily Synthesis" (max 100 words). 
    Focus on the convergence of biology and machine. Use terms like "Signal detected," "Trajectory," "Neural integration."
    
    TASK 2: Identify the top 50 most significant items based on the user's goal: "Seamless experience between human and computer."
    
    Return ONLY the Synthesis paragraph. (For this MVP code, we will just return the synthesis and sort the list locally).
    """

    try:
        client = openai.OpenAI(api_key=API_KEY)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": "You are a helpful BCI research assistant."},
                      {"role": "user", "content": prompt}],
            max_tokens=200
        )
        synthesis = response.choices[0].message.content.strip()
        
        # In a full version, we'd ask the LLM to return JSON of IDs to filter the list.
        # For now, we trust the LLM for the text and just return the latest 50 items.
        return articles[:50], synthesis
        
    except Exception as e:
        print(f"LLM Error: {e}")
        return articles[:50], "Neural uplink unstable. Unable to generate synthesis. Raw feed loaded."

# --- API ENDPOINTS ---

@app.get("/")
def health_check():
    return {"status": "online", "system": "NeuroSync Cortex"}

@app.get("/feed", response_model=FeedResponse)
async def get_feed(background_tasks: BackgroundTasks):
    """
    Returns the daily feed. 
    Uses a caching strategy: serves memory cache if fresh (< 4 hours), 
    otherwise triggers a refresh.
    """
    global cache
    
    # Check if cache is valid (e.g., 4 hours)
    now = datetime.now()
    if cache["data"] and cache["last_updated"] and (now - cache["last_updated"] < timedelta(hours=4)):
        return cache["data"]
    
    # If no cache or stale, fetch new data
    # 1. Gather raw data
    print("Initiating Neural Handshake...")
    papers = fetch_arxiv_papers()
    news = fetch_web_news()
    all_raw = papers + news
    
    # 2. Process with LLM
    final_list, synthesis = await llm_curation(all_raw)
    
    # 3. Construct response
    response = FeedResponse(
        synthesis=synthesis,
        timestamp=now.isoformat(),
        articles=final_list
    )
    
    # 4. Update Cache
    cache["data"] = response
    cache["last_updated"] = now
    
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)