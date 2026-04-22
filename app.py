import logging
from fastapi import FastAPI
import uvicorn
import yt_dlp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

api = FastAPI(title="UL Sniper (Nuclear Edition)")

@api.get("/api/health")
def health_check():
    return {"status": "200 OK", "engine": "Nuclear Decryptor Online 🔥"}

@api.get("/api/download")
def extract_media(url: str):
    logger.info(f"🎯 Nuking Target: {url}")
    
    try:
        # The Ultimate Decryptor Engine Settings
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True, # We only want the link, not the file!
            'age_limit': 99,       # Automatically bypasses all age gates natively
            'noplaylist': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Let the library handle the xHamster decryption automatically
            info = ydl.extract_info(url, download=False)
            
            # Format the duration
            raw_dur = info.get('duration')
            if raw_dur:
                m, s = divmod(int(raw_dur), 60)
                h, m = divmod(m, 60)
                duration = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            else:
                duration = "Unknown"

            return {
                "title": info.get('title', 'Unknown Title'),
                "thumbnail": info.get('thumbnail'),
                "duration": duration,
                "stream_url": info.get('url') # The fully decrypted raw stream link!
            }
            
    except Exception as e:
        logger.error(f"❌ Nuke Failed: {e}")
        return {"error": f"Extraction failed: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=8000)
