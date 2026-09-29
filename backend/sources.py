from __future__ import annotations

from urllib.parse import urlparse


async def fetch_public_page(url: str | None) -> dict:
    if not url:
        return {"status": "unavailable", "source_url": None, "text": "", "metadata": {}, "error": "No profile URL supplied."}
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return {"status": "failed", "source_url": url, "text": "", "metadata": {}, "error": "Only valid HTTPS public URLs are accepted."}
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                if response and response.status in (401, 403, 429):
                    return {"status": "blocked", "source_url": url, "text": "", "metadata": {"http_status": response.status}, "error": "The public page denied automated access."}
                await page.wait_for_timeout(700)
                title = await page.title()
                description = await page.locator('meta[name="description"]').get_attribute("content")
                text = await page.locator("body").inner_text(timeout=5000)
                text = " ".join(text.split())[:12000]
                if not text and not description:
                    return {"status": "empty", "source_url": url, "text": "", "metadata": {"title": title}, "error": "No public profile text was available."}
                return {"status": "success", "source_url": url, "text": text, "metadata": {"title": title, "description": description}}
            finally:
                await browser.close()
    except Exception as exc:
        return {"status": "failed", "source_url": url, "text": "", "metadata": {}, "error": str(exc)[:400]}


async def fetch_public_profile(linkedin_url: str | None, instagram_url: str | None) -> dict:
    linkedin_result = await fetch_public_page(linkedin_url) if linkedin_url else None
    instagram_result = await fetch_public_page(instagram_url) if instagram_url else None
    results = [result for result in (linkedin_result, instagram_result) if result]
    good = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] not in ("success", "unavailable")]
    return {"status": "success" if good else (failed[0]["status"] if failed else "unavailable"),
            "text": "\n".join(r["text"] for r in good), "results": results,
            "linkedin_text": linkedin_result["text"] if linkedin_result else "",
            "instagram_text": instagram_result["text"] if instagram_result else "",
            "error": "; ".join(r["error"] for r in failed) if failed else None}
