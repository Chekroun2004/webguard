"""
Unit tests for Phase 2 active scanners and Crawler — Étape 7.

Strategy: each test mocks the scanner's network methods so no real HTTP calls are made.
Active scanners accept config["pages"] (list of CrawledPage) to avoid crawling in tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.scanners.crawler import CrawledPage, Crawler, Form
from app.scanners.csrf import CsrfScanner
from app.scanners.directory_listing import DirectoryListingScanner
from app.scanners.open_redirect import OpenRedirectScanner
from app.scanners.sqli import SqliScanner
from app.scanners.xss import XssScanner

# ── HTML fixtures ─────────────────────────────────────────────────────────────

HTML_LINKS = """
<html><body>
  <a href="/page1">Page 1</a>
  <a href="/page2">Page 2</a>
  <a href="https://evil.com/external">External</a>
</body></html>
"""

HTML_FORM_SEARCH = """
<html><body>
  <form action="/search" method="post">
    <input name="q" type="text">
    <input type="submit" value="Go">
  </form>
</body></html>
"""

HTML_FORM_WITH_CSRF = """
<html><body>
  <form action="/submit" method="post">
    <input name="name" type="text">
    <input name="_token" type="hidden" value="abc123">
    <input type="submit">
  </form>
</body></html>
"""

HTML_FORM_WITHOUT_CSRF = """
<html><body>
  <form action="/submit" method="post">
    <input name="name" type="text">
    <input type="submit">
  </form>
</body></html>
"""

HTML_GET_FORM = """
<html><body>
  <form action="/search" method="get">
    <input name="q" type="text">
    <input type="submit">
  </form>
</body></html>
"""

HTML_DIR_LISTING = """
<html><body>
  <h1>Index of /uploads/</h1>
  <ul>
    <li><a href="file.txt">file.txt</a></li>
  </ul>
</body></html>
"""

ROBOTS_DISALLOW_ADMIN = "User-agent: *\nDisallow: /admin/\n"
ROBOTS_ALLOW_ALL = "User-agent: *\nDisallow:\n"


def _empty_page(url: str = "https://example.com/") -> dict:
    return {"status": 200, "html": "<html></html>", "headers": {}}


def _make_page(
    url: str = "https://example.com/",
    forms: list[Form] | None = None,
    links: list[str] | None = None,
) -> CrawledPage:
    return CrawledPage(url=url, forms=forms or [], links=links or [])


def _make_form(
    action: str = "https://example.com/search",
    method: str = "post",
    inputs: list[dict] | None = None,
) -> Form:
    return Form(
        action=action,
        method=method,
        inputs=inputs or [{"name": "q", "type": "text", "value": ""}],
    )


# ── Crawler ───────────────────────────────────────────────────────────────────


class TestCrawler:
    async def test_returns_start_url_as_first_page(self):
        crawler = Crawler()
        with patch.object(crawler, "_fetch_page", AsyncMock(return_value=_empty_page())):
            with patch.object(crawler, "_fetch_robots", AsyncMock(return_value=ROBOTS_ALLOW_ALL)):
                pages = await crawler.crawl("https://example.com", {})
        assert len(pages) >= 1
        assert pages[0].url == "https://example.com/"

    async def test_follows_internal_links(self):
        crawler = Crawler()

        async def mock_fetch(url: str, **_kwargs) -> dict:
            if url == "https://example.com/":
                return {"status": 200, "html": HTML_LINKS, "headers": {}}
            return _empty_page(url)

        with patch.object(crawler, "_fetch_page", side_effect=mock_fetch):
            with patch.object(crawler, "_fetch_robots", AsyncMock(return_value=ROBOTS_ALLOW_ALL)):
                pages = await crawler.crawl(
                    "https://example.com", {"max_depth": 1, "max_pages": 20}
                )
        urls = [p.url for p in pages]
        assert any("page1" in u for u in urls)
        assert any("page2" in u for u in urls)

    async def test_ignores_external_links(self):
        crawler = Crawler()

        async def mock_fetch(url: str, **_kwargs) -> dict:
            if "evil.com" in url:
                pytest.fail(f"Should not fetch external URL: {url}")
            return {"status": 200, "html": HTML_LINKS, "headers": {}}

        with patch.object(crawler, "_fetch_page", side_effect=mock_fetch):
            with patch.object(crawler, "_fetch_robots", AsyncMock(return_value=ROBOTS_ALLOW_ALL)):
                await crawler.crawl("https://example.com", {"max_depth": 1, "max_pages": 20})

    async def test_max_depth_zero_crawls_only_start(self):
        crawler = Crawler()
        with patch.object(
            crawler,
            "_fetch_page",
            AsyncMock(return_value={"status": 200, "html": HTML_LINKS, "headers": {}}),
        ):
            with patch.object(crawler, "_fetch_robots", AsyncMock(return_value=ROBOTS_ALLOW_ALL)):
                pages = await crawler.crawl(
                    "https://example.com", {"max_depth": 0, "max_pages": 20}
                )
        assert len(pages) == 1
        assert pages[0].url == "https://example.com/"

    async def test_extracts_forms_from_page(self):
        crawler = Crawler()
        with patch.object(
            crawler,
            "_fetch_page",
            AsyncMock(return_value={"status": 200, "html": HTML_FORM_SEARCH, "headers": {}}),
        ):
            with patch.object(crawler, "_fetch_robots", AsyncMock(return_value=ROBOTS_ALLOW_ALL)):
                pages = await crawler.crawl(
                    "https://example.com", {"max_depth": 0, "max_pages": 10}
                )
        assert len(pages) == 1
        assert len(pages[0].forms) == 1
        form = pages[0].forms[0]
        assert "search" in form.action
        assert form.method == "post"
        assert any(i["name"] == "q" for i in form.inputs)

    async def test_respects_robots_txt_disallow(self):
        crawler = Crawler()
        html_with_admin = '<html><body><a href="/admin/">Admin</a></body></html>'

        async def mock_fetch(url: str, **_kwargs) -> dict:
            if "/admin/" in url:
                pytest.fail(f"Should not crawl disallowed URL: {url}")
            return {"status": 200, "html": html_with_admin, "headers": {}}

        with patch.object(crawler, "_fetch_page", side_effect=mock_fetch):
            with patch.object(
                crawler,
                "_fetch_robots",
                AsyncMock(return_value=ROBOTS_DISALLOW_ADMIN),
            ):
                await crawler.crawl("https://example.com", {"max_depth": 1, "max_pages": 20})


# ── XssScanner ────────────────────────────────────────────────────────────────


class TestXssScanner:
    async def test_reflected_xss_flagged(self):
        scanner = XssScanner()
        page = _make_page(forms=[_make_form()])

        async def mock_submit(action, method, data, **_kwargs):
            payload = next(iter(data.values()))
            return {"status": 200, "body": f"Results for {payload}"}

        with patch.object(scanner, "_submit_form", side_effect=mock_submit):
            findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert any(f.name == "Cross-Site Scripting (XSS)" for f in findings)

    async def test_no_reflection_no_finding(self):
        scanner = XssScanner()
        page = _make_page(forms=[_make_form()])

        async def mock_submit(action, method, data, **_kwargs):
            return {"status": 200, "body": "No results found."}

        with patch.object(scanner, "_submit_form", side_effect=mock_submit):
            findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert findings == []

    async def test_no_forms_no_findings(self):
        scanner = XssScanner()
        page = _make_page(forms=[])
        findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert findings == []

    async def test_xss_severity_is_high(self):
        scanner = XssScanner()
        page = _make_page(forms=[_make_form()])

        async def mock_submit(action, method, data, **_kwargs):
            payload = next(iter(data.values()))
            return {"status": 200, "body": payload}

        with patch.object(scanner, "_submit_form", side_effect=mock_submit):
            findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert all(f.severity == "high" for f in findings)

    async def test_multiple_inputs_tested(self):
        scanner = XssScanner()
        form = _make_form(
            inputs=[
                {"name": "first", "type": "text", "value": ""},
                {"name": "last", "type": "text", "value": ""},
            ]
        )
        page = _make_page(forms=[form])
        call_count = 0

        async def mock_submit(action, method, data, **_kwargs):
            nonlocal call_count
            call_count += 1
            return {"status": 200, "body": "safe"}

        with patch.object(scanner, "_submit_form", side_effect=mock_submit):
            await scanner.scan("https://example.com", {"pages": [page]})
        assert call_count >= 2


# ── SqliScanner ───────────────────────────────────────────────────────────────


class TestSqliScanner:
    async def test_sql_error_in_response_flagged(self):
        scanner = SqliScanner()
        page = _make_page(forms=[_make_form()])

        async def mock_submit(action, method, data, **_kwargs):
            return {
                "status": 500,
                "body": "You have an error in your SQL syntax near ''",
            }

        with patch.object(scanner, "_submit_form", side_effect=mock_submit):
            findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert any(f.name == "SQL Injection" for f in findings)

    async def test_no_sql_error_no_finding(self):
        scanner = SqliScanner()
        page = _make_page(forms=[_make_form()])

        async def mock_submit(action, method, data, **_kwargs):
            return {"status": 200, "body": "Everything is fine."}

        with patch.object(scanner, "_submit_form", side_effect=mock_submit):
            findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert findings == []

    async def test_no_forms_no_findings(self):
        scanner = SqliScanner()
        page = _make_page(forms=[])
        findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert findings == []

    async def test_ora_error_flagged(self):
        scanner = SqliScanner()
        page = _make_page(forms=[_make_form()])

        async def mock_submit(action, method, data, **_kwargs):
            return {"status": 200, "body": "ORA-00933: SQL command not properly ended"}

        with patch.object(scanner, "_submit_form", side_effect=mock_submit):
            findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert any(f.name == "SQL Injection" for f in findings)

    async def test_sqli_severity_is_critical(self):
        scanner = SqliScanner()
        page = _make_page(forms=[_make_form()])

        async def mock_submit(action, method, data, **_kwargs):
            return {"status": 200, "body": "SQLSTATE[42000]: Syntax error"}

        with patch.object(scanner, "_submit_form", side_effect=mock_submit):
            findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert all(f.severity == "critical" for f in findings)


# ── OpenRedirectScanner ───────────────────────────────────────────────────────


class TestOpenRedirectScanner:
    async def test_external_redirect_flagged(self):
        scanner = OpenRedirectScanner()

        async def mock_fetch(url: str, **_kwargs) -> dict:
            return {
                "status": 302,
                "headers": {"location": "https://evil.com/"},
                "body": "",
                "final_url": "https://evil.com/",
            }

        with patch.object(scanner, "_fetch", mock_fetch):
            findings = await scanner.scan(
                "https://example.com",
                {"pages": [_make_page(links=["https://example.com/?url=https://evil.com"])]},
            )
        assert any(f.name == "Open Redirect" for f in findings)

    async def test_no_redirect_params_no_findings(self):
        scanner = OpenRedirectScanner()
        page = _make_page(links=["https://example.com/about"])
        findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert findings == []

    async def test_internal_redirect_not_flagged(self):
        scanner = OpenRedirectScanner()

        async def mock_fetch(url: str, **_kwargs) -> dict:
            return {
                "status": 302,
                "headers": {"location": "https://example.com/home"},
                "body": "",
                "final_url": "https://example.com/home",
            }

        page = _make_page(links=["https://example.com/?redirect=https://example.com/home"])
        with patch.object(scanner, "_fetch", mock_fetch):
            findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert findings == []

    async def test_redirect_params_are_probed(self):
        scanner = OpenRedirectScanner()
        probed_urls: list[str] = []

        async def mock_fetch(url: str, **_kwargs) -> dict:
            probed_urls.append(url)
            return {"status": 200, "headers": {}, "body": "", "final_url": url}

        page = _make_page(links=["https://example.com/go?next=/home&return=/dashboard"])
        with patch.object(scanner, "_fetch", mock_fetch):
            await scanner.scan("https://example.com", {"pages": [page]})
        assert len(probed_urls) >= 2


# ── CsrfScanner ───────────────────────────────────────────────────────────────


class TestCsrfScanner:
    async def test_post_form_without_csrf_token_flagged(self):
        scanner = CsrfScanner()
        page = _make_page(
            forms=[
                _make_form(
                    method="post",
                    inputs=[{"name": "email", "type": "email", "value": ""}],
                )
            ]
        )
        findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert any(f.name == "Missing CSRF Protection" for f in findings)

    async def test_post_form_with_csrf_token_not_flagged(self):
        scanner = CsrfScanner()
        page = _make_page(
            forms=[
                _make_form(
                    method="post",
                    inputs=[
                        {"name": "email", "type": "email", "value": ""},
                        {"name": "_token", "type": "hidden", "value": "abc"},
                    ],
                )
            ]
        )
        findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert findings == []

    async def test_get_form_not_flagged(self):
        scanner = CsrfScanner()
        page = _make_page(
            forms=[
                _make_form(
                    method="get",
                    inputs=[{"name": "q", "type": "text", "value": ""}],
                )
            ]
        )
        findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert findings == []

    async def test_no_forms_no_findings(self):
        scanner = CsrfScanner()
        findings = await scanner.scan("https://example.com", {"pages": [_make_page()]})
        assert findings == []

    async def test_csrf_severity_is_high(self):
        scanner = CsrfScanner()
        page = _make_page(
            forms=[
                _make_form(
                    method="post",
                    inputs=[{"name": "data", "type": "text", "value": ""}],
                )
            ]
        )
        findings = await scanner.scan("https://example.com", {"pages": [page]})
        assert all(f.severity == "high" for f in findings)

    async def test_csrf_token_variations_accepted(self):
        scanner = CsrfScanner()
        for token_name in ["csrf_token", "csrfmiddlewaretoken", "authenticity_token"]:
            page = _make_page(
                forms=[
                    _make_form(
                        method="post",
                        inputs=[
                            {"name": "data", "type": "text", "value": ""},
                            {"name": token_name, "type": "hidden", "value": "x"},
                        ],
                    )
                ]
            )
            findings = await scanner.scan("https://example.com", {"pages": [page]})
            assert findings == [], f"Token '{token_name}' should be accepted"


# ── DirectoryListingScanner ───────────────────────────────────────────────────


class TestDirectoryListingScanner:
    async def test_index_of_in_body_flagged(self):
        scanner = DirectoryListingScanner()
        with patch.object(
            scanner,
            "_check_dir",
            AsyncMock(return_value={"status": 200, "body": "<h1>Index of /uploads/</h1>"}),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert any(f.name == "Directory Listing Enabled" for f in findings)

    async def test_normal_page_not_flagged(self):
        scanner = DirectoryListingScanner()
        with patch.object(
            scanner,
            "_check_dir",
            AsyncMock(return_value={"status": 200, "body": "<h1>Welcome</h1>"}),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_403_not_flagged(self):
        scanner = DirectoryListingScanner()
        with patch.object(
            scanner,
            "_check_dir",
            AsyncMock(return_value={"status": 403, "body": "Forbidden"}),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert findings == []

    async def test_multiple_dirs_checked(self):
        scanner = DirectoryListingScanner()
        checked: list[str] = []

        async def mock_check(url: str, **_kwargs) -> dict:
            checked.append(url)
            return {"status": 403, "body": ""}

        with patch.object(scanner, "_check_dir", side_effect=mock_check):
            await scanner.scan("https://example.com", {})
        assert len(checked) >= 3

    async def test_directory_listing_severity_is_medium(self):
        scanner = DirectoryListingScanner()
        with patch.object(
            scanner,
            "_check_dir",
            AsyncMock(
                return_value={
                    "status": 200,
                    "body": "Index of / - Parent Directory",
                }
            ),
        ):
            findings = await scanner.scan("https://example.com", {})
        assert all(f.severity == "medium" for f in findings)
