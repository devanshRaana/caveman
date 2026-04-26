"""
JARVIS Skill — Web Search
Searches the web using DuckDuckGo (no API key needed).
Falls back gracefully when offline.
"""
from jarvis.skills.base import BaseSkill
from jarvis.utils.connectivity import is_online
from jarvis.logger import logger


class WebSearchSkill(BaseSkill):
    name = "web_search"
    priority = 25

    def can_handle(self, text: str) -> bool:
        triggers = ["search", "google", "look up", "find online",
                     "search the web", "search for", "what is", "who is"]
        return self._contains_any(text, triggers)

    def execute(self, text: str) -> str:
        return self.execute_action("web_search", {"query": text})

    def execute_action(self, action: str, params: dict) -> str:
        query = params.get("query", params.get("_raw", ""))
        if not query:
            return "What would you like me to search for, Sir?"

        if not is_online():
            return f"I'm currently offline, Sir. I can't search the web right now. I'll try to answer from my own knowledge."

        # Suppress annoying RuntimeWarning from DDGS
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    is_news = any(w in query.lower() for w in ["news", "latest", "update", "current", "today"])
                    
                    results = []
                    if is_news:
                        results = list(ddgs.news(query, max_results=5))
                    
                    if not results:
                        results = list(ddgs.text(query, max_results=5))
                        
                    if not results and len(query.split()) > 2:
                        clean_query = " ".join([w for w in query.split() if w.lower() not in ["then", "give", "me", "some", "on", "the", "about", "what", "is"]])
                        results = list(ddgs.text(clean_query, max_results=3))
            except Exception as e:
                logger.error(f"WebSearch DDGS error: {e}")
                results = []

        if not results:
            # Fallback to Wikipedia REST API for deep searching facts
            try:
                import urllib.request
                import json
                # Clean query for Wikipedia
                wiki_query = query.replace(" ", "_")
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_query}"
                req = urllib.request.Request(url, headers={'User-Agent': 'JARVIS/2.2'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    if "extract" in data:
                        return f"[WEB SEARCH RESULTS FOR '{query}']\nRESULT 1:\nTITLE: Wikipedia - {data.get('title', query)}\nDATAPOINT: {data['extract']}\n\n"
            except Exception:
                pass
                
            return f"[WEB SEARCH FAILED: No results found for '{query}']"

        response = f"[WEB SEARCH RESULTS FOR '{query}']\n"
        for i, r in enumerate(results[:5], 1):
            title = r.get("title", "No title")
            body = r.get("body", "")
            
            title = title.encode("ascii", errors="ignore").decode("ascii")
            body = body.encode("ascii", errors="ignore").decode("ascii")
            
            if len(body) > 300:
                body = body[:300] + "..."
            response += f"RESULT {i}:\nTITLE: {title}\nDATAPOINT: {body}\n\n"

        logger.info(f"WebSearch: Found {len(results)} results for '{query}'")
        return response.strip()

    def _browser_fallback(self, query: str) -> str:
        """Fall back to opening search in Chrome."""
        import subprocess
        import urllib.parse
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"
        try:
            subprocess.Popen(["cmd", "/c", "start", url], shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"I've opened a Google search for '{query}' in your browser, Sir."
        except Exception as e:
            return f"I couldn't perform the search, Sir: {e}"
