#!/usr/bin/env python3
"""
Simple browser automation script using Playwright.
Usage: python browser.py <command> [args]
"""

import sys
import json
import asyncio
from playwright.async_api import async_playwright

async def navigate_and_extract(url, selector=None):
    """Navigate to URL and extract content."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle')
            
            if selector:
                # Extract specific element
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                else:
                    content = f"Element '{selector}' not found"
            else:
                # Extract page title and main content
                title = await page.title()
                # Try to get main content area
                content_selectors = ['main', 'article', '.content', '#content', 'body']
                content = ""
                for sel in content_selectors:
                    element = await page.query_selector(sel)
                    if element:
                        content = await element.inner_text()
                        break
                
                result = {
                    'title': title,
                    'url': url,
                    'content': content[:5000] + ('...' if len(content) > 5000 else '')
                }
                return json.dumps(result, indent=2)
            
            return content
            
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            await browser.close()

async def take_screenshot(url, filename='screenshot.png'):
    """Take screenshot of webpage."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle')
            await page.screenshot(path=filename, full_page=True)
            return f"Screenshot saved to {filename}"
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            await browser.close()

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python browser.py navigate <url> [selector]")
        print("  python browser.py screenshot <url> [filename]")
        return
    
    command = sys.argv[1]
    
    if command == 'navigate':
        if len(sys.argv) < 3:
            print("Error: URL required")
            return
        url = sys.argv[2]
        selector = sys.argv[3] if len(sys.argv) > 3 else None
        result = asyncio.run(navigate_and_extract(url, selector))
        print(result)
    
    elif command == 'screenshot':
        if len(sys.argv) < 3:
            print("Error: URL required")
            return
        url = sys.argv[2]
        filename = sys.argv[3] if len(sys.argv) > 3 else 'screenshot.png'
        result = asyncio.run(take_screenshot(url, filename))
        print(result)
    
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()