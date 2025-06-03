from flask import Flask, request, Response
import requests
from urllib.parse import urlparse, urljoin, quote, unquote
import re
from bs4 import BeautifulSoup
import time
import json
import os
import base64
import zlib

dl = Flask(__name__)

GLOBAL_HEADERS = {}
HEADERS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'headers.json')

APP_PY_STYLE_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/33.0 Mobile/15E148 Safari/605.1.15",
    "Referer": "https://google.com/",
    "Origin": "https://google.com"
}

def decode_param_value(encoded_value_str):
    if not encoded_value_str:
        return ""
    try:
        padding_needed = len(encoded_value_str) % 4
        if padding_needed:
            encoded_value_str += '=' * (4 - padding_needed)

        compressed_bytes = base64.urlsafe_b64decode(encoded_value_str.encode('utf-8'))
        original_value_bytes = zlib.decompress(compressed_bytes)
        original_value = original_value_bytes.decode('utf-8')
        return original_value
    except Exception as e:
        raise ValueError(f"Failed to decode/decompress parameter value: {e}")

def encode_uri_for_sub_request(uri_string):
    encoded_bytes = zlib.compress(uri_string.encode('utf-8'))
    return base64.urlsafe_b64encode(encoded_bytes).decode('utf-8').rstrip('=')

def load_global_headers():
    global GLOBAL_HEADERS
    default_ua = "PythonProxy/1.3 (GlobalDefaultUA)"
    try:
        with open(HEADERS_FILE_PATH, 'r') as f:
            loaded_headers = json.load(f)
            GLOBAL_HEADERS['User-Agent'] = str(loaded_headers.get('User-Agent', default_ua) or default_ua).strip()
            GLOBAL_HEADERS['Referer'] = str(loaded_headers.get('Referer', '')).strip()
            GLOBAL_HEADERS['Origin'] = str(loaded_headers.get('Origin', '')).strip()
            if not GLOBAL_HEADERS.get('User-Agent'): GLOBAL_HEADERS['User-Agent'] = default_ua
            if not GLOBAL_HEADERS.get('Referer'): del GLOBAL_HEADERS['Referer']
            if not GLOBAL_HEADERS.get('Origin'):  del GLOBAL_HEADERS['Origin']
    except FileNotFoundError:
        GLOBAL_HEADERS = {"User-Agent": default_ua}
    except json.JSONDecodeError:
        GLOBAL_HEADERS = {"User-Agent": default_ua}
    except Exception:
        GLOBAL_HEADERS = {"User-Agent": default_ua}

KEY_CACHE = {}
KEY_CACHE_DURATION_SECONDS = 60 * 60
KEY_GRABBER_INTERNAL_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'

def _fetch_key_data_from_daddylive(daddylive_stream_url, stream_id_for_key_logging):
    log_prefix = f"[KeyGrab-{stream_id_for_key_logging}]"
    session = requests.Session()
    session.headers.update({'User-Agent': KEY_GRABBER_INTERNAL_USER_AGENT,'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9', 'DNT': '1'})
    response_stream_page = session.get(daddylive_stream_url, timeout=15)
    response_stream_page.raise_for_status()
    stream_html = response_stream_page.text
    embed_url = None
    soup = BeautifulSoup(stream_html, 'html.parser')
    iframe_candidates = soup.find_all('iframe', src=re.compile(r'daddylivehd\.php'))
    if iframe_candidates:
        embed_url = urljoin(daddylive_stream_url, iframe_candidates[0]['src'])
    else:
        match = re.search(r"https?:\/\/[^\s'\"]+daddylivehd\.php\?id=\d+", stream_html)
        if match: embed_url = match.group(0)
        else: raise Exception(f'{log_prefix} Could not locate embed URL')
    parsed_daddylive_url = urlparse(daddylive_stream_url)
    embed_page_headers = {'Referer': daddylive_stream_url,'Origin': f"{parsed_daddylive_url.scheme}://{parsed_daddylive_url.netloc}",'User-Agent': KEY_GRABBER_INTERNAL_USER_AGENT}
    response_embed_page = session.get(embed_url, headers=embed_page_headers, timeout=15)
    response_embed_page.raise_for_status()
    embed_html = response_embed_page.text
    def find_var(name, html_content):
        match_re = re.search(fr"var\s+{name}\s*=\s*['\"]([^'\"]+)['\"]", html_content)
        if not match_re: raise Exception(f"{log_prefix} Couldn't find {name}")
        return match_re.group(1)
    channel_key_val, auth_ts, auth_rnd, auth_sig = find_var('channelKey', embed_html), find_var('authTs', embed_html), find_var('authRnd', embed_html), find_var('authSig', embed_html)
    parsed_embed_url_obj = urlparse(embed_url)
    session.headers.update({'Origin': f"{parsed_embed_url_obj.scheme}://{parsed_embed_url_obj.netloc}",'Referer': embed_url,'sec-ch-ua': '"Not.A/Brand";v="99", "Chromium";v="136"','sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"macOS"','sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'cross-site'})
    auth_url = f"https://top2new.newkso.ru/auth.php?channel_id={channel_key_val}&ts={auth_ts}&rnd={auth_rnd}&sig={auth_sig}"
    session.get(auth_url, timeout=15).raise_for_status()
    lookup_url = f"https://allupplay.xyz/server_lookup.php?channel_id={channel_key_val}"
    session.get(lookup_url, timeout=15).raise_for_status()
    key_fetch_url = f"https://key2.keylocking.ru/wmsxx.php?test=true&name={channel_key_val}&number=1"
    response_key = session.get(key_fetch_url, timeout=15)
    response_key.raise_for_status()
    key_data = response_key.content
    if not key_data: raise Exception(f"{log_prefix} Key fetch failed: Empty key data")
    return key_data


def _fetch_key_data_from_topembed(topembed_page_url, stream_id_for_key_logging):
    """
    Scrape a Topembed page directly, authenticate via its API endpoints,
    and return the raw 16‑byte AES key for the requested channel.
    """
    log_prefix = f"[TopembedKeyGrab-{stream_id_for_key_logging}]"
    session = requests.Session()
    session.headers.update({
        'User-Agent': KEY_GRABBER_INTERNAL_USER_AGENT,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'DNT': '1'
    })

    # 1. Download the page containing the JS variables
    try:
        resp_page = session.get(topembed_page_url, timeout=15)
        resp_page.raise_for_status()
    except Exception as e:
        raise Exception(f"{log_prefix} Unable to fetch Topembed page: {e}")
    html = resp_page.text

    def find_var_from_html(var_name, html_content):
        normalized_html = html_content.replace('\xa0', ' ')
        m = re.search(rf"var\s+{re.escape(var_name)}\s*=\s*['\"]([^'\"]+)['\"]", normalized_html)
        if not m:
            raise Exception(f"{log_prefix} Could not locate JS variable '{var_name}'")
        return m.group(1)

    try:
        channel_key = find_var_from_html('channelKey', html)
        auth_ts     = find_var_from_html('authTs', html)
        auth_rnd    = find_var_from_html('authRnd', html)
        auth_sig    = find_var_from_html('authSig', html)
    except Exception as e:
        raise

    # Prepare common headers for subsequent requests
    parsed_src = urlparse(topembed_page_url)
    session.headers.update({
        'Origin': f"{parsed_src.scheme}://{parsed_src.netloc}",
        'Referer': topembed_page_url,
        'sec-ch-ua': '"Not.A/Brand";v="99", "Chromium";v="136"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site'
    })

    # 2. Authenticate tokens
    auth_url = (
        "https://top2new.newkso.ru/auth.php"
        f"?channel_id={channel_key}&ts={auth_ts}&rnd={auth_rnd}&sig={auth_sig}"
    )
    try:
        session.get(auth_url, timeout=15).raise_for_status()
    except Exception as e:
        raise Exception(f"{log_prefix} auth.php failed: {e}")

    lookup_url = urljoin(topembed_page_url, f"/server_lookup.php?channel_id={channel_key}")
    try:
        session.get(lookup_url, timeout=15).raise_for_status()
    except Exception as e:
        raise Exception(f"{log_prefix} server_lookup failed: {e}")

    # 3. Fetch the raw key
    key_fetch_url = f"https://key.keylocking.ru/wmsxx.php?test=true&name={channel_key}&number=1"
    try:
        resp_key = session.get(key_fetch_url, timeout=15)
        resp_key.raise_for_status()
    except Exception as e:
        raise Exception(f"{log_prefix} key fetch failed: {e}")

    key_data = resp_key.content
    if not key_data:
        raise Exception(f"{log_prefix} Empty key data")

    return key_data




def get_stream_id_from_url(m3u_url_str):
    match = re.search(r'(premium\d+)', m3u_url_str, re.IGNORECASE)
    return match.group(1) if match else None

def detect_m3u_type_for_h_mode(content):
    if "#EXTM3U" in content and "#EXTINF" in content and not any(line.startswith("#EXT-X-STREAM-INF") or line.startswith("#EXT-X-TARGETDURATION") for line in content.splitlines()):
        return "m3u"
    if "#EXTM3U" in content:
        return "m3u8"
    return "unknown"

def _process_h_mode_m3u8_content(m3u_content_str, base_url_for_internal_paths, encoded_h_params_query_string):
    modified_m3u8_lines = []
    for line_content in m3u_content_str.splitlines():
        line_content = line_content.strip()
        if line_content.startswith("#EXT-X-KEY") and 'URI="' in line_content:
            key_match = re.search(r'URI="([^"]+)"', line_content)
            if key_match:
                original_key_uri_in_manifest = key_match.group(1)
                absolute_key_uri = urljoin(base_url_for_internal_paths, original_key_uri_in_manifest)
                encoded_absolute_key_uri = encode_uri_for_sub_request(absolute_key_uri)
                proxied_key_uri = f"/h_mode/key?url={encoded_absolute_key_uri}&{encoded_h_params_query_string}"
                line_content = line_content.replace(original_key_uri_in_manifest, proxied_key_uri)
        elif line_content and not line_content.startswith("#"):
            original_resource_uri_in_manifest = line_content
            absolute_resource_uri = urljoin(base_url_for_internal_paths, original_resource_uri_in_manifest)
            encoded_absolute_resource_uri = encode_uri_for_sub_request(absolute_resource_uri)
            proxied_resource_uri = f"/h_mode/ts?url={encoded_absolute_resource_uri}&{encoded_h_params_query_string}"
            line_content = proxied_resource_uri
        modified_m3u8_lines.append(line_content)
    return "\n".join(modified_m3u8_lines)

@dl.route('/proxy/m3u')
def proxy_m3u():
    encoded_main_url_param = request.args.get('url', '').strip()
    if not encoded_main_url_param:
        return "Error: Missing 'url' parameter", 400

    topembed_source_encoded = request.args.get('h_topembed', '').strip()
    custom_h_args_from_url = {k: v for k, v in request.args.items() if k.lower().startswith('h_') and k.lower() not in ('url','h_topembed')}

    try:
        actual_target_m3u_url = decode_param_value(encoded_main_url_param)
        if not actual_target_m3u_url:
             return "Error: Decoded target URL is empty", 400

        if custom_h_args_from_url:
            decoded_custom_h_params = {}
            for key, encoded_value in custom_h_args_from_url.items():
                decoded_custom_h_params[unquote(key[2:]).replace("_", "-")] = decode_param_value(encoded_value)

            h_mode_headers_for_m3u_fetch = {**APP_PY_STYLE_DEFAULT_HEADERS, **decoded_custom_h_params}

            response = requests.get(actual_target_m3u_url, headers=h_mode_headers_for_m3u_fetch, allow_redirects=True, timeout=10)
            response.raise_for_status()
            final_url_after_redirects = response.url
            m3u_content_text = response.text

            file_type = detect_m3u_type_for_h_mode(m3u_content_text)

            if file_type == "m3u":
                return Response(m3u_content_text, content_type="audio/x-mpegurl")

            parsed_final_url = urlparse(final_url_after_redirects)
            base_url_for_paths = f"{parsed_final_url.scheme}://{parsed_final_url.netloc}{parsed_final_url.path.rsplit('/', 1)[0]}/"

            encoded_h_params_query_string = "&".join([
                f"{h_key}={h_encoded_val}" for h_key, h_encoded_val in custom_h_args_from_url.items()
            ])

            modified_m3u8_content = _process_h_mode_m3u8_content(m3u_content_text, base_url_for_paths, encoded_h_params_query_string)
            return Response(modified_m3u8_content, content_type="application/vnd.apple.mpegurl")
        else:
            m3u_fetch_headers = GLOBAL_HEADERS.copy()
            response = requests.get(actual_target_m3u_url, headers=m3u_fetch_headers, allow_redirects=True, timeout=10)
            response.raise_for_status()
            final_url_after_redirects = response.url
            m3u_content = response.text
            stream_id_for_key = get_stream_id_from_url(actual_target_m3u_url) or get_stream_id_from_url(final_url_after_redirects)
            parsed_m3u_url = urlparse(final_url_after_redirects)
            base_url_for_m3u8_paths = f"{parsed_m3u_url.scheme}://{parsed_m3u_url.netloc}{parsed_m3u_url.path.rsplit('/', 1)[0]}/"
            modified_m3u8_lines = []
            for line in m3u_content.splitlines():
                line = line.strip()
                if line.startswith("#EXT-X-KEY") and 'URI="' in line:
                    if stream_id_for_key:
                        new_key_uri = f"/keygrab/actual_key/{stream_id_for_key}" + (f"?topembed_source={topembed_source_encoded}" if topembed_source_encoded else "")
                        line = re.sub(r'URI="[^"]+"', f'URI="{new_key_uri}"', line)
                    else:
                        original_key_uri_match = re.search(r'URI="([^"]+)"', line)
                        if original_key_uri_match:
                            original_key_uri_path = original_key_uri_match.group(1)
                            absolute_original_key_uri = urljoin(base_url_for_m3u8_paths, original_key_uri_path)
                            proxied_original_key = f"/keygrab/original_key_passthrough?url={quote(absolute_original_key_uri)}"
                            line = re.sub(r'URI="[^"]+"', f'URI="{proxied_original_key}"', line)
                elif line and not line.startswith("#"):
                    segment_path = line
                    absolute_segment_url = urljoin(base_url_for_m3u8_paths, segment_path)
                    proxied_segment_url = f"/keygrab/ts?url={quote(absolute_segment_url)}"
                    line = proxied_segment_url
                modified_m3u8_lines.append(line)
            modified_m3u8_content = "\n".join(modified_m3u8_lines)
            return Response(modified_m3u8_content, content_type="application/vnd.apple.mpegurl")

    except ValueError as ve:
         return f"Error processing input parameters: {str(ve)}", 400
    except requests.RequestException as e:
        path_type = "h_mode" if custom_h_args_from_url else "keygrab"
        return f"Error fetching M3U ({path_type}): {str(e)}", 500
    except Exception as e:
        path_type = "h_mode" if custom_h_args_from_url else "keygrab"
        return f"An unexpected error occurred ({path_type}): {str(e)}", 500

@dl.route('/h_mode/key')
def h_mode_proxy_key():
    encoded_key_url_param = request.args.get('url', '').strip()
    if not encoded_key_url_param:
        return "Error: Missing 'url' (h_mode key)", 400

    try:
        key_url = decode_param_value(encoded_key_url_param)
        if not key_url: return "Error: Decoded key URL is empty", 400

        headers_for_key = {}
        for key, encoded_value in request.args.items():
            if key.lower().startswith("h_") and key.lower() != 'url':
                headers_for_key[unquote(key[2:]).replace("_", "-")] = decode_param_value(encoded_value)

        response = requests.get(key_url, headers=headers_for_key, allow_redirects=True, timeout=10)
        response.raise_for_status()
        return Response(response.content, content_type="application/octet-stream")
    except ValueError as ve:
        return f"Error processing parameters (h_mode key): {str(ve)}", 400
    except requests.RequestException as e:
        return f"Error Key (h_mode): {str(e)}", 500

@dl.route('/h_mode/ts')
def h_mode_proxy_ts():
    encoded_ts_url_param = request.args.get('url', '').strip()
    if not encoded_ts_url_param:
        return "Error: Missing 'url' (h_mode ts)", 400

    try:
        actual_ts_url = decode_param_value(encoded_ts_url_param)
        if not actual_ts_url: return "Error: Decoded TS URL is empty", 400

        headers_for_ts_fetch = {}
        encoded_h_params_for_sub_sub_requests_list = []

        for key, encoded_value in request.args.items():
            if key.lower().startswith("h_") and key.lower() != 'url':
                 headers_for_ts_fetch[unquote(key[2:]).replace("_", "-")] = decode_param_value(encoded_value)
                 encoded_h_params_for_sub_sub_requests_list.append(f"{key}={encoded_value}")

        encoded_h_params_query_string = "&".join(encoded_h_params_for_sub_sub_requests_list)

        response = requests.get(actual_ts_url, headers=headers_for_ts_fetch, stream=True, allow_redirects=True, timeout=(5,25))
        response.raise_for_status()

        content_type_header = response.headers.get("content-type", "").lower()
        parsed_actual_ts_url_path = urlparse(actual_ts_url).path.lower()

        is_playlist_by_content_type = "mpegurl" in content_type_header or "x-mpegurl" in content_type_header
        is_playlist_by_extension = parsed_actual_ts_url_path.endswith((".m3u", ".m3u8"))

        is_likely_playlist = False
        if content_type_header == "video/mp2t":
            is_likely_playlist = False
        elif is_playlist_by_content_type or is_playlist_by_extension:
            is_likely_playlist = True

        if is_likely_playlist:
            playlist_content_bytes = b"".join(response.iter_content(chunk_size=8192))
            playlist_content_str = playlist_content_bytes.decode('utf-8', errors='ignore')

            nested_playlist_base_url_for_paths = f"{urlparse(actual_ts_url).scheme}://{urlparse(actual_ts_url).netloc}{urlparse(actual_ts_url).path.rsplit('/', 1)[0]}/"

            modified_playlist_content = _process_h_mode_m3u8_content(playlist_content_str, nested_playlist_base_url_for_paths, encoded_h_params_query_string)
            return Response(modified_playlist_content, content_type="application/vnd.apple.mpegurl")
        else:
            return Response(response.iter_content(chunk_size=32768), content_type="video/mp2t")

    except ValueError as ve:
        return f"Error processing parameters (h_mode ts): {str(ve)}", 400
    except requests.exceptions.Timeout:
        return f"Timeout TS (h_mode): {actual_ts_url if 'actual_ts_url' in locals() else 'unknown'}", 504
    except requests.RequestException as e:
        return f"Error TS (h_mode): {str(e)}", 500

@dl.route('/keygrab/actual_key/<stream_id_for_key>')
def keygrab_proxy_actual_key(stream_id_for_key):
    topembed_source_encoded = request.args.get('topembed_source', '').strip()
    cache_key = f"{stream_id_for_key}|{topembed_source_encoded}"

    now = time.time()
    if cache_key in KEY_CACHE:
        cache_entry = KEY_CACHE[cache_key]
        if not cache_entry.get('fetching', False) and cache_entry.get('key_data') and \
           (now - cache_entry.get('timestamp', 0) < KEY_CACHE_DURATION_SECONDS):
            return Response(cache_entry['key_data'], content_type="application/octet-stream")
        elif cache_entry.get('fetching'):
            return "Key fetch in progress", 503
    KEY_CACHE[cache_key] = {"fetching": True, "timestamp": now}
    try:
        numeric_id_match = re.search(r'\d+', stream_id_for_key)
        if not numeric_id_match: raise ValueError("Invalid stream_id for key")
        numeric_id = numeric_id_match.group(0)
        daddylive_url = f"https://daddylive.dad/stream/stream-{numeric_id}.php"
        key_data = _fetch_key_data_internal(daddylive_url, stream_id_for_key)
        KEY_CACHE[cache_key] = {"key_data": key_data, "timestamp": time.time(), "fetching": False}
        return Response(key_data, content_type="application/octet-stream")
    except Exception as e:
        KEY_CACHE.pop(cache_key, None)
        return f"Error Key (keygrab): {str(e)}", 500

@dl.route('/keygrab/ts')
def keygrab_proxy_ts():
    ts_url = request.args.get('url', '').strip()
    if not ts_url: return "Error: Missing 'url' (keygrab ts)", 400
    ts_fetch_headers = GLOBAL_HEADERS.copy()
    try:
        response = requests.get(ts_url, headers=ts_fetch_headers, stream=True, allow_redirects=True, timeout=(5, 25))
        response.raise_for_status()
        content_type = response.headers.get("content-type", "video/mp2t")
        return Response(response.iter_content(chunk_size=32768), content_type=content_type)
    except requests.exceptions.Timeout:
        return f"Timeout TS (keygrab): {ts_url}", 504
    except requests.RequestException as e:
        return f"Error TS (keygrab): {str(e)}", 500

@dl.route('/keygrab/original_key_passthrough')
def keygrab_proxy_original_key_passthrough():
    key_url = request.args.get('url', '').strip()
    if not key_url: return "Error: Missing 'url' (keygrab passthrough)", 400
    key_fetch_headers = GLOBAL_HEADERS.copy()
    try:
        response = requests.get(key_url, headers=key_fetch_headers, allow_redirects=True, timeout=10)
        response.raise_for_status()
        return Response(response.content, content_type="application/octet-stream")
    except requests.RequestException as e:
        return f"Error Key (passthrough): {str(e)}", 500

if __name__ == '__main__':
    load_global_headers()
    dl.run(host="0.0.0.0", port=8888, debug=False, threaded=True)
