import os
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import arxiv
from duckduckgo_search import DDGS
import uvicorn
import google.generativeai as genai
from google.api_core import exceptions

# --- CONFIGURATION ---
API_KEY = os.getenv("LLM_API_KEY", "") 

# Configure Gemini with REST transport to avoid gRPC errors on Render
if API_KEY:
    genai.configure(api_key=API_KEY, transport='rest')

app = FastAPI(title="NeuroSync Cortex")

# Enable CORS
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

# --- FETCHING LOGIC ---
def fetch_arxiv_papers(limit=30) -> List[Article]:
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
    except Exception as e:
        print(f"News fetch error: {e}")
        return []
    return results

async def llm_curation(articles: List[Article]) -> tuple[List[Article], str]:
    if not API_KEY:
        return articles[:50], "Synthesis Offline: API Key missing in Cortex configuration."

    # Prepare prompt
    titles = "\n".join([f"- {a.title}" for a in articles[:30]])
    
    prompt = f"""
    You are the "Cortex" of a BCI research dashboard. 
    Here is a list of incoming data streams (papers and news):
    
    {titles}
    
    TASK: Write a high-level, sci-fi style "Daily Synthesis" (max 80 words). 
    Focus on the convergence of biology and machine. Use terms like "Signal detected," "Trajectory," "Neural integration."
    Do NOT use bullet points. Write it as a single briefing paragraph.
    """

    # Model Fallback Chain
    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            synthesis = response.text.strip()
            return articles[:50], synthesis
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            continue

    return articles[:50], "Neural uplink unstable. All AI models unresponsive."

# --- ENDPOINTS ---
@app.get("/")
def health_check():
    return {"status": "online", "system": "NeuroSync Cortex"}

@app.get("/feed", response_model=FeedResponse)
async def get_feed(background_tasks: BackgroundTasks):
    global cache
    
    # 1 Hour Cache
    now = datetime.now()
    if cache["data"] and cache["last_updated"] and (now - cache["last_updated"] < timedelta(hours=1)):
        return cache["data"]
    
    # Fetch Fresh
    papers = fetch_arxiv_papers()
    news = fetch_web_news()
    all_raw = papers + news
    
    # AI Synthesis
    final_list, synthesis = await llm_curation(all_raw)
    
    response = FeedResponse(
        synthesis=synthesis,
        timestamp=now.isoformat(),
        articles=final_list
    )
    
    cache["data"] = response
    cache["last_updated"] = now
    
    return response