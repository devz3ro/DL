from flask import Flask, request, Response
import requests
from urllib.parse import urlparse, urljoin, quote
import re
from bs4 import BeautifulSoup
import time
import json
import os

dl = Flask(__name__)

GLOBAL_HEADERS = {}
HEADERS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'headers.json')

def load_global_headers():
    global GLOBAL_HEADERS
    default_ua = "PythonProxy/1.3 (GlobalDefaultUA)"
    try:
        with open(HEADERS_FILE_PATH, 'r') as f:
            loaded_headers = json.load(f)
            GLOBAL_HEADERS['User-Agent'] = str(loaded_headers.get('User-Agent', default_ua) or default_ua).strip()
            GLOBAL_HEADERS['Referer'] = str(loaded_headers.get('Referer', '')).strip()
            GLOBAL_HEADERS['Origin'] = str(loaded_headers.get('Origin', '')).strip()

            if not GLOBAL_HEADERS.get('User-Agent'):
                 GLOBAL_HEADERS['User-Agent'] = default_ua
            if not GLOBAL_HEADERS.get('Referer'): del GLOBAL_HEADERS['Referer']
            if not GLOBAL_HEADERS.get('Origin'):  del GLOBAL_HEADERS['Origin']

        print(f"[INFO] Successfully loaded global headers from {HEADERS_FILE_PATH}")
    except FileNotFoundError:
        print(f"[WARN] headers.json not found at {HEADERS_FILE_PATH}. Using default User-Agent.")
        GLOBAL_HEADERS = {"User-Agent": default_ua}
    except json.JSONDecodeError:
        print(f"[ERROR] Could not decode headers.json. Check format. Using default User-Agent.")
        GLOBAL_HEADERS = {"User-Agent": default_ua}
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred loading headers.json: {e}. Using default User-Agent.")
        GLOBAL_HEADERS = {"User-Agent": default_ua}
    finally:
        print(f"[INFO] Global Headers to be used by proxy: {GLOBAL_HEADERS}")


KEY_CACHE = {}
KEY_CACHE_DURATION_SECONDS = 60 * 60
KEY_GRABBER_INTERNAL_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'

def _fetch_key_data_internal(daddylive_stream_url, stream_id_for_key_logging):
    log_prefix = f"[KeyGrab-{stream_id_for_key_logging}]"
    print(f"{log_prefix} Starting key fetch for: {daddylive_stream_url}")
    session = requests.Session()
    session.headers.update({
        'User-Agent': KEY_GRABBER_INTERNAL_USER_AGENT,
        'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9', 'DNT': '1'
    })
    print(f"{log_prefix} Phase 1: GET {daddylive_stream_url}")
    response_stream_page = session.get(daddylive_stream_url, timeout=15)
    response_stream_page.raise_for_status()
    stream_html = response_stream_page.text
    embed_url = None
    soup = BeautifulSoup(stream_html, 'html.parser')
    iframe_candidates = soup.find_all('iframe', src=re.compile(r'daddylivehd\.php'))
    if iframe_candidates:
        embed_url = urljoin(daddylive_stream_url, iframe_candidates[0]['src'])
        print(f"{log_prefix} Phase 2: Found <iframe src> -> {embed_url}")
    else:
        match = re.search(r"https?:\/\/[^\s'\"]+daddylivehd\.php\?id=\d+", stream_html)
        if match: embed_url = match.group(0); print(f"{log_prefix} Phase 2: Found embed via regex -> {embed_url}")
        else: raise Exception(f'{log_prefix} Could not locate embed URL on stream page')
    print(f"{log_prefix} Phase 3: GET {embed_url}")
    parsed_daddylive_url = urlparse(daddylive_stream_url)
    embed_page_headers = {
        'Referer': daddylive_stream_url,
        'Origin': f"{parsed_daddylive_url.scheme}://{parsed_daddylive_url.netloc}",
        'User-Agent': KEY_GRABBER_INTERNAL_USER_AGENT
    }
    response_embed_page = session.get(embed_url, headers=embed_page_headers, timeout=15)
    response_embed_page.raise_for_status()
    embed_html = response_embed_page.text
    def find_var(name, html_content):
        match = re.search(fr"var\s+{name}\s*=\s*['\"]([^'\"]+)['\"]", html_content)
        if not match: raise Exception(f"{log_prefix} Couldn't find {name} in embed code")
        return match.group(1)
    channel_key_val = find_var('channelKey', embed_html)
    auth_ts = find_var('authTs', embed_html)
    auth_rnd = find_var('authRnd', embed_html)
    auth_sig = find_var('authSig', embed_html)
    print(f"{log_prefix} Phase 4: Parsed auth params for {channel_key_val}")
    parsed_embed_url_obj = urlparse(embed_url)
    session.headers.update({
        'Origin': f"{parsed_embed_url_obj.scheme}://{parsed_embed_url_obj.netloc}",
        'Referer': embed_url,
        'sec-ch-ua': '"Not.A/Brand";v="99", "Chromium";v="136"',
        'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'cross-site',
    })
    auth_url = (f"https://top2new.newkso.ru/auth.php?channel_id={channel_key_val}&ts={auth_ts}&rnd={auth_rnd}&sig={auth_sig}")
    print(f"{log_prefix} Phase 5: GET {auth_url}")
    session.get(auth_url, timeout=15).raise_for_status()
    lookup_url = f"https://alldownplay.xyz/server_lookup.php?channel_id={channel_key_val}"
    print(f"{log_prefix} Phase 6: GET {lookup_url}")
    session.get(lookup_url, timeout=15).raise_for_status()
    key_fetch_url = (f"https://key2.keylocking.ru/wmsxx.php?test=true&name={channel_key_val}&number=1")
    print(f"{log_prefix} Phase 7: GET {key_fetch_url}")
    response_key = session.get(key_fetch_url, timeout=15)
    response_key.raise_for_status()
    key_data = response_key.content
    if not key_data: raise Exception(f"{log_prefix} Key fetch failed: Received empty key data")
    print(f"{log_prefix} Phase 7: Key for {channel_key_val} successfully fetched ({len(key_data)} bytes).")
    return key_data

def get_stream_id_from_url(m3u_url_str):
    match = re.search(r'(premium\d+)', m3u_url_str, re.IGNORECASE)
    return match.group(1) if match else None

@app.route('/proxy/m3u')
def proxy_m3u():
    original_m3u_url = request.args.get('url', '').strip()
    if not original_m3u_url:
        return "Error: Missing 'url' parameter", 400

    m3u_fetch_headers = GLOBAL_HEADERS.copy()
    print(f"[ProxyM3U] Request for: {original_m3u_url}")
    try:
        response = requests.get(original_m3u_url, headers=m3u_fetch_headers, allow_redirects=True, timeout=10)
        response.raise_for_status()
        final_url_after_redirects = response.url
        m3u_content = response.text
        stream_id_for_key = get_stream_id_from_url(original_m3u_url) or get_stream_id_from_url(final_url_after_redirects)
        parsed_m3u_url = urlparse(final_url_after_redirects)
        base_url_for_m3u8_paths = f"{parsed_m3u_url.scheme}://{parsed_m3u_url.netloc}{parsed_m3u_url.path.rsplit('/', 1)[0]}/"
        modified_m3u8_lines = []
        for line in m3u_content.splitlines():
            line = line.strip()
            if line.startswith("#EXT-X-KEY") and 'URI="' in line:
                if stream_id_for_key:
                    new_key_uri = f"/proxy/actual_key/{stream_id_for_key}"
                    line = re.sub(r'URI="[^"]+"', f'URI="{new_key_uri}"', line)
                else:
                    original_key_uri_match = re.search(r'URI="([^"]+)"', line)
                    if original_key_uri_match:
                        original_key_uri = urljoin(base_url_for_m3u8_paths, original_key_uri_match.group(1))
                        proxied_original_key = f"/proxy/original_key_passthrough?url={quote(original_key_uri)}"
                        line = re.sub(r'URI="[^"]+"', f'URI="{proxied_original_key}"', line)
            elif line and not line.startswith("#"):
                segment_url = urljoin(base_url_for_m3u8_paths, line)
                proxied_segment_url = f"/proxy/ts?url={quote(segment_url)}"
                line = proxied_segment_url
            modified_m3u8_lines.append(line)
        modified_m3u8_content = "\n".join(modified_m3u8_lines)
        return Response(modified_m3u8_content, content_type="application/vnd.apple.mpegurl")
    except Exception as e:
        print(f"[ProxyM3U] Error processing {original_m3u_url}: {str(e)}")
        return f"Error processing M3U/M3U8: {str(e)}", 500

@app.route('/proxy/actual_key/<stream_id_for_key>')
def proxy_actual_key(stream_id_for_key):
    now = time.time()
    if stream_id_for_key in KEY_CACHE:
        cache_entry = KEY_CACHE[stream_id_for_key]
        if not cache_entry.get('fetching', False) and \
           cache_entry.get('key_data') and \
           (now - cache_entry.get('timestamp', 0) < KEY_CACHE_DURATION_SECONDS):
            return Response(cache_entry['key_data'], content_type="application/octet-stream")
        elif cache_entry.get('fetching'):
            print(f"[ProxyKey] Key fetch already in progress for {stream_id_for_key}")
            return "Key fetch in progress", 503
    KEY_CACHE[stream_id_for_key] = {"fetching": True, "timestamp": now}
    try:
        numeric_id_match = re.search(r'\d+', stream_id_for_key)
        if not numeric_id_match: raise ValueError("Invalid stream_id format for key")
        numeric_id = numeric_id_match.group(0)
        daddylive_url = f"https://daddylive.dad/stream/stream-{numeric_id}.php"
        key_data = _fetch_key_data_internal(daddylive_url, stream_id_for_key)
        KEY_CACHE[stream_id_for_key] = {"key_data": key_data, "timestamp": time.time(), "fetching": False}
        print(f"[ProxyKey] Successfully fetched and cached key for {stream_id_for_key}")
        return Response(key_data, content_type="application/octet-stream")
    except Exception as e:
        KEY_CACHE.pop(stream_id_for_key, None)
        print(f"[ProxyKey] Error fetching key for {stream_id_for_key}: {str(e)}")
        return f"Error during key retrieval: {str(e)}", 500

@app.route('/proxy/ts')
def proxy_ts():
    ts_url = request.args.get('url', '').strip()
    if not ts_url: return "Error: Missing 'url' parameter", 400
    ts_fetch_headers = GLOBAL_HEADERS.copy()
    try:
        response = requests.get(ts_url, headers=ts_fetch_headers, stream=True, allow_redirects=True, timeout=(5, 25))
        response.raise_for_status()
        return Response(response.iter_content(chunk_size=32768), content_type=response.headers.get("content-type", "video/mp2t"))
    except requests.exceptions.Timeout:
        print(f"[ProxyTS] Timeout downloading segment {ts_url}")
        return f"Timeout downloading TS segment: {ts_url}", 504
    except requests.RequestException as e:
        print(f"[ProxyTS] Error downloading segment {ts_url}: {str(e)}")
        return f"Error downloading TS segment: {str(e)}", 500

@app.route('/proxy/original_key_passthrough')
def proxy_original_key_passthrough():
    key_url = request.args.get('url', '').strip()
    if not key_url: return "Error: Missing 'url' parameter for the original key", 400
    key_fetch_headers = GLOBAL_HEADERS.copy()
    try:
        response = requests.get(key_url, headers=key_fetch_headers, allow_redirects=True, timeout=10)
        response.raise_for_status()
        return Response(response.content, content_type="application/octet-stream")
    except requests.RequestException as e:
        return f"Error downloading AES-128 key (passthrough): {str(e)}", 500

if __name__ == '__main__':
    load_global_headers()
    # Example: gunicorn --workers 4 --bind 0.0.0.0:8888 dl:dl
    app.run(host="0.0.0.0", port=8888, debug=False, threaded=True)
  
