"""
Tushare Documentation Crawler

This script crawls the Tushare Pro documentation pages using Playwright.
It navigates through the left sidebar navigation tree and saves each page as HTML.

The crawler uses a recursive approach:
1. Visit each page
2. Extract all navigation links from the sidebar on that page
3. Recursively visit any new links found

Usage:
    python crawl_tushare_docs.py

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
import glob
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
from playwright.async_api import async_playwright, Page, Browser


# Configuration
BASE_URL = "https://tushare.pro/document/2"
OUTPUT_DIR = Path(__file__).parent
DELAY_BETWEEN_PAGES = 0.8  # seconds between page loads to be polite
DEBUG_SCREENSHOT = False  # Save screenshot for debugging
CLEAN_OLD_FILES = True  # Clean old .htm files before crawling


def sanitize_filename(name: str) -> str:
    """Convert a string to a valid filename"""
    # Remove or replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove leading/trailing spaces and dots
    name = name.strip(". ")
    # Limit length
    if len(name) > 100:
        name = name[:100]
    return name


def clean_old_files():
    """Remove old .htm files from the output directory"""
    htm_files = list(OUTPUT_DIR.glob("*.htm"))
    png_files = list(OUTPUT_DIR.glob("_debug*.png"))

    all_files = htm_files + png_files
    if all_files:
        print(f"Cleaning {len(all_files)} old files...")
        for f in all_files:
            try:
                f.unlink()
            except:
                pass


def get_doc_id(url: str) -> str:
    """Extract doc_id from URL for deduplication"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    doc_id = params.get("doc_id", [""])[0]
    return doc_id if doc_id else url


async def wait_for_page_load(page: Page):
    """Wait for the page content to fully load"""
    try:
        # Wait for network to be idle (all requests finished)
        await page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass
    # Additional wait for JavaScript rendering
    await asyncio.sleep(0.5)


async def get_sidebar_links(page: Page) -> list:
    """
    Extract all navigation links from the current page's sidebar.
    Returns list of dicts with 'text', 'url', 'doc_id'
    """
    links = []
    seen_doc_ids = set()

    # Find all links to document pages
    selector = 'a[href*="/document/"]'

    try:
        items = await page.query_selector_all(selector)

        for item in items:
            try:
                text = await item.inner_text()
                href = await item.get_attribute("href")

                if not text or not href:
                    continue

                text = text.strip()
                if not text:
                    continue

                # Build full URL
                if href.startswith("/"):
                    full_url = f"https://tushare.pro{href}"
                elif href.startswith("http"):
                    full_url = href
                else:
                    full_url = urljoin(BASE_URL, href)

                # Get doc_id for deduplication
                doc_id = get_doc_id(full_url)

                # Skip duplicates
                if doc_id in seen_doc_ids:
                    continue

                seen_doc_ids.add(doc_id)
                links.append(
                    {
                        "text": text,
                        "url": full_url,
                        "doc_id": doc_id,
                    }
                )
            except:
                continue
    except:
        pass

    return links


async def save_page_content(page: Page, filename: str, title: str):
    """Save the current page content as HTML"""
    try:
        # Get the main content area
        content = await page.content()

        # Save to file
        filepath = OUTPUT_DIR / f"{filename}.htm"

        # Add a comment at the top with the title
        html_with_title = f"<!-- Page: {title} -->\n{content}"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_with_title)

        print(f"  Saved: {filepath.name}")
        return True
    except Exception as e:
        print(f"  Error saving {filename}: {e}")
        return False


async def crawl_page(page: Page, url: str, title: str, index: int) -> bool:
    """Navigate to a page and save its content"""
    try:
        print(f"[{index}] Crawling: {title}")
        print(f"    URL: {url}")

        # Navigate to the page
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait for content to load
        await wait_for_page_load(page)

        # Additional wait for dynamic content
        await asyncio.sleep(0.5)

        # Generate filename
        filename = f"{index:03d}_{sanitize_filename(title)}"

        # Save the page
        success = await save_page_content(page, filename, title)

        return success
    except Exception as e:
        print(f"  Error crawling {title}: {e}")
        return False


async def recursive_crawl(
    page: Page, visited_doc_ids: set, all_links: list, depth: int = 0
):
    """
    Recursively discover all links by visiting each page and extracting sidebar links.
    This ensures we find ALL leaf nodes, even deeply nested ones.
    """
    indent = "  " * depth
    current_url = page.url
    print(f"{indent}🔍 Scanning page: {current_url}")

    # Get links from current page
    new_links = await get_sidebar_links(page)
    print(f"{indent}📋 Found {len(new_links)} links on this page")

    new_count = 0
    for i, link in enumerate(new_links, 1):
        doc_id = link["doc_id"]

        # Skip if already visited
        if doc_id in visited_doc_ids:
            print(
                f"{indent}  [{i}/{len(new_links)}] ⏭️  Skip (already visited): {link['text']}"
            )
            continue

        visited_doc_ids.add(doc_id)
        all_links.append(link)
        new_count += 1

        print(f"{indent}  [{i}/{len(new_links)}] ✅ New: {link['text']}")
        print(f"{indent}      URL: {link['url']}")

        # Visit this page to discover more links
        try:
            print(f"{indent}      🚀 Visiting to find sub-pages...")
            await page.goto(link["url"], wait_until="domcontentloaded", timeout=30000)
            await wait_for_page_load(page)

            # Recursively get more links from this page
            await recursive_crawl(page, visited_doc_ids, all_links, depth + 1)

        except Exception as e:
            print(f"{indent}      ❌ Error visiting {link['text']}: {e}")
            continue

    print(
        f"{indent}✨ Completed scanning. Found {new_count} new pages at depth {depth}"
    )
    print(f"{indent}📊 Total discovered so far: {len(all_links)} pages")


async def main():
    """Main crawler function with recursive link discovery"""
    print("=" * 60)
    print("Tushare Documentation Crawler (Recursive)")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Clean old files if configured
    if CLEAN_OLD_FILES:
        clean_old_files()

    async with async_playwright() as p:
        # Launch browser
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        try:
            # Navigate to the main documentation page
            print(f"Navigating to {BASE_URL}...")
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await wait_for_page_load(page)
            await asyncio.sleep(2)

            # Phase 1: Recursively discover ALL links
            print("\nPhase 1: Discovering all documentation pages...")
            print("-" * 60)

            visited_doc_ids = set()
            all_links = []

            # Add the base page
            base_doc_id = get_doc_id(BASE_URL)
            visited_doc_ids.add(base_doc_id)

            # Recursively discover all links
            await recursive_crawl(page, visited_doc_ids, all_links)

            print(f"\nDiscovered {len(all_links)} unique documentation pages")
            print("-" * 60)

            # Phase 2: Save all pages
            print("\nPhase 2: Saving all pages...")
            print("-" * 60)

            # Save the main page first
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await wait_for_page_load(page)
            await save_page_content(page, "000_沪深股票_主页", "沪深股票_主页")

            # Crawl and save each discovered page
            success_count = 0
            fail_count = 0

            for i, link in enumerate(all_links, start=1):
                success = await crawl_page(page, link["url"], link["text"], i)

                if success:
                    success_count += 1
                else:
                    fail_count += 1

                # Be polite - add delay between requests
                await asyncio.sleep(DELAY_BETWEEN_PAGES)

            print()
            print("=" * 60)
            print("Crawling Complete!")
            print(f"  Success: {success_count}")
            print(f"  Failed: {fail_count}")
            print(f"  Total: {len(all_links)}")
            print("=" * 60)

        except Exception as e:
            print(f"Error during crawling: {e}")
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
