# app/services/security.py
import asyncio
import logging
import time
from collections import defaultdict
from urllib.parse import urlparse
from aiohttp import ClientSession, ClientTimeout
# УБРАНО: from app.config import settings

logger = logging.getLogger(__name__)

# In-memory cache for URL safety checks
url_safety_cache = {}
CACHE_TTL = 3600  # 1 hour cache

# Rate limiting storage
user_requests = defaultdict(list)

def is_rate_limited(user_id: int, settings) -> bool: # Принимаем settings как аргумент
    """Check if user is rate limited."""
    current_time = time.time()
    # Удаляем старые запросы за пределами окна
    user_requests[user_id] = [
        req_time for req_time in user_requests[user_id]
        if current_time - req_time < settings.rate_limit_window # Используем settings
    ]

    if len(user_requests[user_id]) >= settings.rate_limit_requests: # Используем settings
        logger.info(f"User {user_id} is rate limited.")
        return True

    user_requests[user_id].append(current_time)
    return False

def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except Exception:
        return False

async def check_url_safety(url: str, settings) -> tuple[bool | None, str | None]: # Принимаем settings как аргумент
    """
    Check URL safety using Google Safe Browsing API with caching.
    Returns: (is_safe: bool, threat_type: str or None)
    """
    if not settings.gsb_api_key: # Используем settings
        logger.warning("GSB_API_KEY not configured, skipping safety check.")
        return (None, "API key not configured")

    if not is_valid_url(url):
        return (None, "Invalid URL format")

    # Check cache first
    current_time = time.time()
    if url in url_safety_cache:
        cached_result, cache_time = url_safety_cache[url]
        if current_time - cache_time < CACHE_TTL:
            logger.info(f"Using cached result for URL: {url[:50]}...")
            return cached_result

    api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={settings.gsb_api_key}" # Используем settings

    payload = {
        "client": {
            "clientId": "qrscanerpro",
            "clientVersion": "2.0.0"
        },
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }

    timeout = ClientTimeout(total=settings.request_timeout) # Используем settings
    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.post(api_url, json=payload) as resp:
                if resp.status != 200:
                    logger.warning(f"Safe Browsing API returned status {resp.status}")
                    return (None, f"API error: {resp.status}")

                result = await resp.json()

                if 'matches' in result and len(result['matches']) > 0:
                    threat = result['matches'][0].get('threatType', 'UNKNOWN')
                    result_tuple = (False, threat)
                else:
                    result_tuple = (True, None)

                # Cache the result
                url_safety_cache[url] = (result_tuple, current_time)
                # Simple cache cleanup
                if len(url_safety_cache) > 1000:
                    old_entries = [k for k, (_, t) in url_safety_cache.items() if current_time - t > CACHE_TTL]
                    for k in old_entries:
                        del url_safety_cache[k]

                return result_tuple

    except asyncio.TimeoutError:
        logger.warning("Safe Browsing API request timed out")
        return (None, "Request timeout")
    except Exception as e:
        logger.error(f"Error checking URL safety: {e}")
        return (None, "API error")
