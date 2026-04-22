import re
import time
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from curl_cffi.requests import AsyncSession

# --- PROFESSIONAL LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

api = FastAPI(title="UL Sniper (Omni-Extractor Ultimate V4)")

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

@api.get("/api/health")
async def health_check():
    return {"status": "200 OK", "engine": "Fortified Omni-Extractor Online 🔥"}

@api.get("/api/download")
async def extract_media(url: str):
    logger.info(f"🎯 Ripping: {url}")
    try:
        # 💀 THE ARMOR: Flawless Modern Chrome Headers to bypass initial Nginx 403
        armor_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

        async with AsyncSession(impersonate="chrome120") as session:
            response = await session.get(url, headers=armor_headers, timeout=15)
            raw_html = response.text
            clean_html = raw_html.replace('\\/', '/')
            
            # --- 1. TITLE ---
            title = "Unknown Title"
            title_match = re.search(r'<meta[\s\S]+?(?:property|name)=["\'](?:og:title|twitter:title)["\'][\s\S]+?content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if title_match:
                title = title_match.group(1)
            else:
                title_match = re.search(r'<title[^>]*>([\s\S]*?)</title>', raw_html, re.IGNORECASE)
                if title_match: title = title_match.group(1)
            title = re.sub(r' - (XVIDEOS\.COM|XNXX\.COM|XXXBP|SexVid\.xxx)$', '', title, flags=re.IGNORECASE)
            title = title.replace(" | xHamster", "").replace(" | PussySpace", "").strip()
            
            # --- 2. THUMBNAIL ---
            thumbnail = None
            thumb_match = re.search(r'<meta[\s\S]+?(?:property|name)=["\'](?:og:image|twitter:image)["\'][\s\S]+?content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if thumb_match: thumbnail = thumb_match.group(1)
            
            # --- 3. DURATION ---
            duration = "Unknown"
            dur_match = re.search(r'"duration"\s*:\s*(\d+)', raw_html)
            if not dur_match:
                dur_match = re.search(r'<meta[\s\S]+?(?:property|itemprop)=["\'](?:video:duration|og:duration|duration|og:video:duration)["\'][\s\S]+?content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if dur_match: 
                duration = format_duration(dur_match.group(1))

            # --- 4. OMNI-STREAM EXTRACTOR ---
            stream_url = None
            
            preload_match = re.search(r'<link[^>]+?href=["\'](https?://[^"\']+\.m3u8[^"\']*)["\'][^>]*?as=["\']fetch["\']', raw_html, re.IGNORECASE)
            if preload_match: stream_url = preload_match.group(1)

            if not stream_url:
                x_match = re.search(r"html5player\.setVideoHLS\(['\"](https?://[^'\"]+)['\"]\)", clean_html)
                if not x_match:
                    x_match = re.search(r"html5player\.setVideoUrlHigh\(['\"](https?://[^'\"]+)['\"]\)", clean_html)
                if x_match: stream_url = x_match.group(1)
            
            if not stream_url:
                kvs_match = re.search(r"(?:video_url|video_alt_url|video_url_hd)\s*:\s*['\"](?:function/[^/]+/)?(https?://[^'\"]+)['\"]", raw_html, re.IGNORECASE)
                if kvs_match: 
                    stream_url = kvs_match.group(1)
                    if 'get_file' in stream_url and 'rnd=' not in stream_url:
                        live_timestamp = int(time.time() * 1000)
                        separator = '&' if '?' in stream_url else '?'
                        stream_url = f"{stream_url}{separator}rnd={live_timestamp}"

            if not stream_url:
                m3u8_links = re.findall(r'(https?://[^\s"\'<>\[\]()]+?\.m3u8[^\s"\'<>\[\]()]*)', clean_html)
                if m3u8_links: stream_url = m3u8_links[0]
                
            if not stream_url:
                mp4_links = re.findall(r'(https?://[^\s"\'<>\[\]()]+?\.mp4[^\s"\'<>\[\]()]*)', clean_html)
                for link in mp4_links:
                    lower_link = link.lower()
                    if not any(bad in lower_link for bad in ['preview', 'thumb', 'poster', '.jpg', '.png', '.webp']):
                        stream_url = link
                        break

            if not stream_url:
                og_vid = re.search(r'<meta[\s\S]+?(?:property|name)=["\'](?:og:video:url|og:video|twitter:player)["\'][\s\S]+?content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
                if og_vid: stream_url = og_vid.group(1)

            if not stream_url:
                vid_src = re.search(r'<link[\s\S]+?rel=["\']video_src["\'][\s\S]+?href=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
                if vid_src: stream_url = vid_src.group(1)

            if not stream_url:
                source_tag = re.search(r'<source[\s\S]+?src=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
                if source_tag: stream_url = source_tag.group(1)

            # ==========================================
            # 5. CDN REDIRECT RESOLVER (Safe Catch Mode)
            # ==========================================
            if stream_url and ('get_file' in stream_url or 'redirect' in stream_url):
                logger.info(f"🕵️‍♂️ Asking Bouncer for Redirect Location: {stream_url[:50]}...")
                try:
                    # 👻 We ONLY pass Referer. Let the session handle everything else.
                    # We set allow_redirects=False to safely catch the Location header!
                    resolve_headers = {"Referer": url, "Accept": "*/*"}
                    resolve_resp = await session.get(
                        stream_url, 
                        headers=resolve_headers, 
                        allow_redirects=False, 
                        timeout=15
                    )
                    # If the Bouncer hands us a 302, we steal the Location!
                    if resolve_resp.status_code in [301, 302, 303, 307, 308]:
                        stream_url = resolve_resp.headers.get("Location", stream_url)
                        logger.info(f"✅ Cracked final CDN vault link: {stream_url[:50]}...")
                    else:
                        logger.warning(f"⚠️ Bouncer returned status {resolve_resp.status_code}")
                except Exception as e:
                    logger.error(f"⚠️ Failed to resolve redirect: {e}")

            if not stream_url:
                return {
                    "error": "Media stream not found. Omni-Extractor exhausted.",
                    "diagnostics": {
                        "downloaded_page_title": title,
                        "html_snippet": raw_html[:300] 
                    }
                }
                
            return {
                "title": title,
                "thumbnail": thumbnail,
                "duration": duration,
                "stream_url": stream_url,
                "headers_needed": {
                    "Referer": url,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            }
            
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}

@api.get("/api/source", response_class=HTMLResponse)
async def get_raw_source(url: str):
    try:
        async with AsyncSession(impersonate="chrome120") as session:
            response = await session.get(url, timeout=15)
            return response.text
    except Exception as e: return f"Error: {str(e)}"

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)
