import re
import logging
from fastapi import FastAPI
import uvicorn
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

api = FastAPI(title="UL Sniper (Launchpad Edition)")

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
    return {"status": "200 OK", "engine": "Launchpad HTTP Ripper is Online 🔥"}

@api.get("/api/download")
async def extract_media(url: str):
    logger.info(f"🎯 Ripping Raw Source from: {url}")
    
    try:
        async with AsyncSession(impersonate="chrome110") as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/"
            }
            
            response = await session.get(url, headers=headers, timeout=15)
            raw_html = response.text
            clean_html = raw_html.replace('\\/', '/') 
            
            title = "Unknown Title"
            thumbnail = None
            duration = "Unknown"
            stream_url = None
            
            title_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if not title_match: title_match = re.search(r'<title>(.*?)</title>', raw_html, re.IGNORECASE)
            if title_match: title = title_match.group(1).strip()

            thumb_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if thumb_match:
                thumbnail = thumb_match.group(1)
                if thumbnail.startswith("//"): thumbnail = "https:" + thumbnail
                thumbnail = thumbnail.replace('_t.jpg', '_p.jpg').replace('_t.webp', '_p.webp')
            
            if not thumbnail:
                raw_jpg = re.search(r"(https?://[^\s\"\'<>\[\]\{\}]+?(?:poster|thumb|cover|snapshot)[^\s\"\'<>\[\]\{\}]*\.jpg)", clean_html, re.IGNORECASE)
                if raw_jpg: thumbnail = raw_jpg.group(1)

            dur_match = re.search(r'<meta\s+(?:property|itemprop)=["\'](?:video:duration|og:duration|duration|og:video:duration)["\']\s+content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if dur_match: duration = format_duration(dur_match.group(1))

            xv_match = re.search(r"html5player\.setVideoHLS\(['\"](https?://[^'\"]+)['\"]\)", clean_html)
            if xv_match: stream_url = xv_match.group(1)
            
            if not stream_url:
                preload_match = re.search(r'<link\s+rel=["\']preload["\'].*?href=["\']([^"\']+\.m3u8[^"\']*)["\']', raw_html, re.IGNORECASE)
                if preload_match: stream_url = preload_match.group(1)
            
            if not stream_url:
                m3u8_match = re.search(r"(https?://[^\s\"\'<>\[\]\{\}]+\.m3u8[^\s\"\'<>\[\]\{\}]*)", clean_html)
                if m3u8_match: stream_url = m3u8_match.group(1)
                
            if not stream_url:
                kvs_match = re.search(r"(?:video_url|video_alt_url|video_url_hd):\s*['\"](?:function/[^/]+/)?(https?://[^'\"]+)['\"]", clean_html)
                if kvs_match: stream_url = kvs_match.group(1)
                
            if not stream_url:
                og_vid = re.search(r'<meta\s+property=["\']og:video(?::url)?["\']\s+content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
                if og_vid: stream_url = og_vid.group(1)

            if not stream_url: return {"error": "Media stream not found in raw HTML. IP bypass worked, but layout is unrecognizable."}
                
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
