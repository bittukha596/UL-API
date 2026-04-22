import re
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

api = FastAPI(title="UL Sniper (Embed Backdoor Edition)")

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
    return {"status": "200 OK"}

@api.get("/api/download")
async def extract_media(url: str):
    logger.info(f"🎯 Initial Target: {url}")
    
    # ==========================================
    # 🚪 THE EMBED BACKDOOR INTERCEPTOR
    # ==========================================
    target_url = url
    if "xhamster.com/videos/" in url:
        # Snatch the ID from the end of the URL and strip any tracking queries
        video_id = url.split('-')[-1].split('?')[0] 
        target_url = f"https://xhamster.com/embed/{video_id}"
        logger.info(f"🚪 Hitting Embed Backdoor: {target_url}")
        
    try:
        async with AsyncSession(impersonate="chrome110") as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                # Spoof the referer so xHamster thinks a random site is loading the embed
                "Referer": "https://www.google.com/" 
            }
            
            response = await session.get(target_url, headers=headers, timeout=15)
            raw_html = response.text
            clean_html = raw_html.replace('\\/', '/')
            
            # --- 1. TITLE (Upgraded to catch `<title >`) ---
            title = "Unknown Title"
            title_match = re.search(r'<title[^>]*>([\s\S]*?)</title>', raw_html, re.IGNORECASE)
            if title_match: title = title_match.group(1).replace(" | xHamster", "").strip()
            
            # --- 2. THUMBNAIL ---
            thumbnail = None
            thumb_match = re.search(r'<meta[\s\S]+?property=["\']og:image["\'][\s\S]+?content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if thumb_match: thumbnail = thumb_match.group(1)
            if not thumbnail:
                raw_jpg = re.search(r"(https?://[^\s\"\'<>\[\]()]+?(?:poster|thumb|cover|snapshot)[^\s\"\'<>\[\]()]*\.jpg)", clean_html, re.IGNORECASE)
                if raw_jpg: thumbnail = raw_jpg.group(1)
            
            # --- 3. DURATION ---
            duration = "Unknown"
            dur_match = re.search(r'<meta[\s\S]+?(?:property|itemprop)=["\'](?:video:duration|og:duration|duration|og:video:duration)["\'][\s\S]+?content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if dur_match: duration = format_duration(dur_match.group(1))

            # --- 4. THE STREAM ---
            stream_url = None
            m3u8_links = re.findall(r'(https?://[^\s"\'<>\[\]()]+?\.m3u8[^\s"\'<>\[\]()]*)', clean_html)
            if m3u8_links: stream_url = m3u8_links[0]
                
            if not stream_url:
                mp4_links = re.findall(r'(https?://[^\s"\'<>\[\]()]+?\.mp4[^\s"\'<>\[\]()]*)', clean_html)
                for link in mp4_links:
                    lower_link = link.lower()
                    if 'preview' not in lower_link and 'thumb' not in lower_link and 'poster' not in lower_link:
                        stream_url = link
                        break

            if not stream_url:
                return {
                    "error": "Media stream not found in Embed Backdoor.",
                    "diagnostics": {
                        "target_used": target_url,
                        "downloaded_page_title": title,
                        "html_snippet": raw_html[:250] 
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
