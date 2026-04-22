import re
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from playwright.async_api import async_playwright

# 💀 THE V2 IMPORT FIX
from playwright_stealth import Stealth 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def format_duration(raw_dur):
    if not raw_dur: return "Unknown"
    raw_dur = str(raw_dur).strip().upper()
    match = re.search(r'P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', raw_dur)
    if match:
        d = int(match.group(1)) if match.group(1) else 0
        h = int(match.group(2)) if match.group(2) else 0
        m = int(match.group(3)) if match.group(3) else 0
        s = int(match.group(4)) if match.group(4) else 0
        total_seconds = (d * 86400) + (h * 3600) + (m * 60) + s
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
    if raw_dur.replace('.', '').isdigit():
        total_seconds = int(float(raw_dur))
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
    return raw_dur

# Global variable to hold the persistent browser in RAM
engine = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔥 Igniting Persistent Chromium Engine...")
    engine["playwright"] = await async_playwright().start()
    engine["browser"] = await engine["playwright"].chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ]
    )
    yield
    logger.info("💀 Shutting down engine...")
    await engine["browser"].close()
    await engine["playwright"].stop()

api = FastAPI(title="UL Sniper (Stealth Assassin V2)", lifespan=lifespan)

@api.get("/api/health")
async def health_check():
    return {"status": "200 OK", "engine": "Playwright Stealth Assassin V2 Online 🔥"}

@api.get("/api/download")
async def extract_media(url: str):
    logger.info(f"🎯 Target Locked: {url}")
    browser = engine.get("browser")
    if not browser:
        return {"error": "Engine offline"}

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    
    # 💀 THE V2 STEALTH INJECTION (Applies to the entire context)
    stealth = Stealth()
    await stealth.apply_stealth_async(context)
    
    page = await context.new_page()
    
    stream_url = None

    # ==========================================
    # 1. THE AD SKIP EXPLOIT & RAM SAVER
    # ==========================================
    async def intercept_route(route):
        request = route.request
        req_url = request.url.lower()
        res_type = request.resource_type

        # Kill visuals to load the DOM instantly
        if res_type in ["image", "stylesheet", "font"]:
            return await route.abort()

        # Block Ad Networks (Forces the video player to bypass the 7s wait)
        ad_keywords = ["vast", "trafficstars", "exoclick", "popunder", "ads", "tracker", "analytics"]
        if any(kw in req_url for kw in ad_keywords):
            return await route.abort()

        return await route.continue_()

    await page.route("**/*", intercept_route)

    # ==========================================
    # 2. THE NETWORK SNIFFER (Snatch & Kill)
    # ==========================================
    async def on_response(response):
        nonlocal stream_url
        res_url = response.url
        status = response.status

        # Catch raw files or 302 Redirects from the Bouncer
        if status in [200, 206, 301, 302] and not stream_url:
            if ".m3u8" in res_url or ".mp4" in res_url or "get_file" in res_url:
                if not any(bad in res_url.lower() for bad in ["preview", "thumb", "poster", ".jpg", ".png"]):
                    if status in [301, 302] and "location" in response.headers:
                        stream_url = response.headers["location"]
                    else:
                        stream_url = res_url

    page.on("response", on_response)

    try:
        # Load the page. Because visuals and ads are blocked, domcontentloaded hits in milliseconds.
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        # Auto-click the play button to force the XHR request.
        try:
            play_selectors = [".play-button", ".vjs-big-play-button", "[aria-label='Play']", ".player-overlay"]
            for selector in play_selectors:
                if await page.locator(selector).count() > 0:
                    await page.locator(selector).first.click(timeout=1000)
                    break
        except Exception:
            pass

        # Wait up to 5 seconds for the sniffer to catch the link
        for _ in range(50):
            if stream_url:
                break
            await asyncio.sleep(0.1)

        # ==========================================
        # 3. METADATA EXTRACTION
        # ==========================================
        content = await page.content()
        
        title = "Unknown Title"
        title_match = re.search(r'<meta[\s\S]+?(?:property|name)=["\'](?:og:title|twitter:title)["\'][\s\S]+?content=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if title_match: title = title_match.group(1)
        else:
            title_match = re.search(r'<title[^>]*>([\s\S]*?)</title>', content, re.IGNORECASE)
            if title_match: title = title_match.group(1)
        title = re.sub(r' - (XVIDEOS\.COM|XNXX\.COM|XXXBP|SexVid\.xxx)$', '', title, flags=re.IGNORECASE).replace(" | xHamster", "").strip()
        
        thumbnail = None
        thumb_match = re.search(r'<meta[\s\S]+?(?:property|name)=["\'](?:og:image|twitter:image)["\'][\s\S]+?content=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if thumb_match: thumbnail = thumb_match.group(1)
        
        duration = "Unknown"
        dur_match = re.search(r'"duration"\s*:\s*(\d+)', content)
        if not dur_match:
            dur_match = re.search(r'<meta[\s\S]+?(?:property|itemprop)=["\'](?:video:duration|og:duration|duration|og:video:duration)["\'][\s\S]+?content=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if dur_match: duration = format_duration(dur_match.group(1))

        if not stream_url:
            return {
                "error": "Media stream not found via network sniff.",
                "diagnostics": {"downloaded_page_title": title}
            }

        return {
            "title": title,
            "thumbnail": thumbnail,
            "duration": duration,
            "stream_url": stream_url,
            "headers_needed": {"Referer": url}
        }

    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}
    finally:
        # Instantly kill the tab to free up RAM
        await context.close()

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)
