"""Web scraping utility."""

import httpx
from bs4 import BeautifulSoup


async def scrape_page(url: str, format: str = "markdown") -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as http:
        r = await http.get(url, headers=headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else url
        main = soup.find("article") or soup.find("main") or soup.find("body")
        text = main.get_text(separator="\n", strip=True) if main else ""

        links = list({a.get("href", "") for a in soup.find_all("a") if a.get("href", "").startswith("http")})

        if format == "markdown":
            # Very basic conversion
            lines = [f"# {title}", "", text]
            content = "\n".join(lines)
        else:
            content = text

        return {
            "url": url,
            "title": title,
            "content": content[:10000],
            "links": links[:50],
        }
