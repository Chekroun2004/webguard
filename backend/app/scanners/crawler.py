"""
Crawler — discovers pages and forms on a target website.

Respects robots.txt, stays within the same domain, limits depth and page count.
Returns a list of CrawledPage objects used by active scanners.
"""

from __future__ import annotations

import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class Form:
    action: str
    method: str  # "get" or "post"
    inputs: list[dict] = field(default_factory=list)


@dataclass
class CrawledPage:
    url: str
    forms: list[Form] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


class Crawler:
    def __init__(self) -> None:
        self._cookies: dict[str, str] = {}

    async def _fetch_page(self, url: str) -> dict:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15, cookies=self._cookies
        ) as client:
            try:
                resp = await client.get(url)
                return {
                    "status": resp.status_code,
                    "html": resp.text,
                    "headers": dict(resp.headers),
                }
            except OSError:
                return {"status": 0, "html": "", "headers": {}}

    async def _fetch_robots(self, base_url: str) -> str:
        robots_url = base_url.rstrip("/") + "/robots.txt"
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=10, cookies=self._cookies
        ) as client:
            try:
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    return resp.text
            except OSError:
                pass
        return ""

    async def crawl(self, start_url: str, config: dict) -> list[CrawledPage]:
        max_depth: int = config.get("max_depth", 2)
        max_pages: int = config.get("max_pages", 50)
        self._cookies = config.get("cookies") or {}

        parsed = urlparse(start_url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        canonical_start = base_origin + (parsed.path or "/")

        robots_txt = await self._fetch_robots(base_origin)
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base_origin + "/robots.txt")
        rp.parse(robots_txt.splitlines())

        visited: set[str] = set()
        pages: list[CrawledPage] = []
        queue: list[tuple[str, int]] = [(canonical_start, 0)]

        while queue and len(pages) < max_pages:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            if not rp.can_fetch("*", url):
                continue
            visited.add(url)

            result = await self._fetch_page(url)
            if result["status"] == 0:
                continue

            soup = BeautifulSoup(result["html"], "html.parser")
            forms = self._extract_forms(soup, url)
            links = self._extract_links(soup, url, base_origin)
            pages.append(CrawledPage(url=url, forms=forms, links=links))

            if depth < max_depth:
                for link in links:
                    if link not in visited:
                        queue.append((link, depth + 1))

        return pages

    def _extract_links(self, soup: BeautifulSoup, page_url: str, base_origin: str) -> list[str]:
        links: list[str] = []
        for tag in soup.find_all("a", href=True):
            href = str(tag["href"]).strip()
            if href.startswith(("#", "mailto:", "javascript:")):
                continue
            absolute = urljoin(page_url, href).split("#")[0]
            parsed = urlparse(absolute)
            if f"{parsed.scheme}://{parsed.netloc}" == base_origin:
                links.append(absolute)
        return list(dict.fromkeys(links))

    def _extract_forms(self, soup: BeautifulSoup, page_url: str) -> list[Form]:
        forms: list[Form] = []
        for form_tag in soup.find_all("form"):
            action = urljoin(page_url, form_tag.get("action") or page_url)
            method = (form_tag.get("method") or "get").lower()
            inputs: list[dict] = []
            for inp in form_tag.find_all(["input", "textarea", "select"]):
                name = inp.get("name")
                if not name:
                    continue
                inp_type = inp.get("type", "text").lower()
                if inp_type in ("submit", "button", "image", "reset"):
                    continue
                inputs.append(
                    {
                        "name": name,
                        "type": inp_type,
                        "value": inp.get("value", ""),
                    }
                )
            forms.append(Form(action=action, method=method, inputs=inputs))
        return forms
