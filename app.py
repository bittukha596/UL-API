import re
import logging
from fastapi import FastAPI
import uvicorn
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

api = FastAPI(title="UL Sniper (Ghost Edition)")

def format_duration(raw_dur):
    if not raw_dur: return "Unknown"
    raw_dur = str(raw_dur).strip()
    match = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', raw_dur.upper())
    if match:
        h = int(match.group(1)) if match.group(1) else 0
        m = int(match.group(2)) if match.group(2) else 0
        s = int(match.group(3)) if match.group(3) else 0
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
    if raw_dur.replace('.', '').isdigit():
        total_seconds = int(float(raw_dur))
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
    return raw_dur

@api.get("/api/health")
async def health_check():
    return {"status": "200 OK", "engine": "Ghost Ripper Online 🔥"}

@api.get("/api/download")
async def extract_media(url: str):
    logger.info(f"🎯 Ripping: {url}")
    try:
        # 👻 THE FIX: Pure impersonation with ZERO custom headers! 
        # This prevents Cloudflare from detecting a User-Agent mismatch.
        async with AsyncSession(impersonate="chrome116") as session:
            response = await session.get(url, timeout=15)
            raw_html = response.text
            clean_html = raw_html.replace('\\/', '/')
            
            # --- 1. TITLE ---
            title = "Unknown Title"
            title_match = re.search(r'<title[^>]*>([\s\S]*?)</title>', raw_html, re.IGNORECASE)
            if title_match: title = title_match.group(1).replace(" | xHamster", "").strip()
            
            # --- 2. THUMBNAIL ---
            thumbnail = None
            thumb_match = re.search(r'<meta[\s\S]+?property=["\']og:image["\'][\s\S]+?content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if thumb_match: thumbnail = thumb_match.group(1)
            
            # --- 3. DURATION ---
            duration = "Unknown"
            dur_match = re.search(r'<meta[\s\S]+?(?:property|itemprop)=["\'](?:video:duration|og:duration|duration|og:video:duration)["\'][\s\S]+?content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if dur_match: duration = format_duration(dur_match.group(1))

            # --- 4. THE STREAM ---
            stream_url = None
            
            # GOLDEN EXTRACTION: Hunts for the exact unencrypted preload link you found in the desktop source
            preload_match = re.search(r'<link[^>]+?href=["\'](https?://[^"\']+\.m3u8[^"\']*)["\'][^>]*?as=["\']fetch["\']', raw_html, re.IGNORECASE)
            if preload_match:
                stream_url = preload_match.group(1)
            
            # Fallback Universal m3u8
            if not stream_url:
                m3u8_links = re.findall(r'(https?://[^\s"\'<>\[\]()]+?\.m3u8[^\s"\'<>\[\]()]*)', clean_html)
                if m3u8_links: stream_url = m3u8_links[0]
                
            # Fallback MP4
            if not stream_url:
                mp4_links = re.findall(r'(https?://[^\s"\'<>\[\]()]+?\.mp4[^\s"\'<>\[\]()]*)', clean_html)
                for link in mp4_links:
                    lower_link = link.lower()
                    if 'preview' not in lower_link and 'thumb' not in lower_link and 'poster' not in lower_link:
                        stream_url = link
                        break

            if not stream_url:
                return {
                    "error": "Media stream not found.",
                    "diagnostics": {
                        "downloaded_page_title": title,
                        "html_snippet": raw_html[:300] 
                    }
                }
                
            return {
                "title": title,
                "thumbnail": thumbnail,
                "duration": duration,
                "stream_url": stream_url
            }
            
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)
