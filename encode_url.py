import urllib.parse
import argparse
import base64
import zlib

PROXY_PREFIX = "http://127.0.0.1:8888/proxy/m3u?url="

def smart_encode_url_for_proxy_compress_base64(target_url, h_referer_val=None, h_origin_val=None, h_user_agent_val=None):
    parsed_target_url = urllib.parse.urlparse(target_url)
    
    target_url_for_proxy_value = urllib.parse.urlunsplit((
        parsed_target_url.scheme,
        parsed_target_url.netloc,
        parsed_target_url.path,
        parsed_target_url.query,
        parsed_target_url.fragment
    ))

    target_url_bytes = target_url_for_proxy_value.encode('utf-8')
    compressed_target_url_bytes = zlib.compress(target_url_bytes)
    encoded_target_url_value_bytes = base64.urlsafe_b64encode(compressed_target_url_bytes)
    encoded_target_url_value = encoded_target_url_value_bytes.decode('utf-8').rstrip('=')
    
    final_url = f"{PROXY_PREFIX}{encoded_target_url_value}"
    
    h_params_to_process = {}
    if h_referer_val:
        h_params_to_process["h_referer"] = h_referer_val
    if h_origin_val:
        h_params_to_process["h_origin"] = h_origin_val
    if h_user_agent_val:
        h_params_to_process["h_User-Agent"] = h_user_agent_val

    for h_key, h_value in h_params_to_process.items():
        h_value_bytes = h_value.encode('utf-8')
        compressed_h_value_bytes = zlib.compress(h_value_bytes)
        encoded_h_value_bytes = base64.urlsafe_b64encode(compressed_h_value_bytes)
        encoded_h_value = encoded_h_value_bytes.decode('utf-8').rstrip('=')
        final_url += f"&{h_key}={encoded_h_value}"
            
    return final_url

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compresses (zlib) and URL-safe Base64 encodes a target URL and specified h_ parameters for a proxy structure, then adds a prefix."
    )
    parser.add_argument("target_url", help="The target web URL to encode (e.g., 'https://player.test/mono.m3u8?md5=12345').")
    parser.add_argument(
        "--h_referer",
        help="Value for the h_referer header for the proxy."
    )
    parser.add_argument(
        "--h_origin",
        help="Value for the h_origin header for the proxy."
    )
    parser.add_argument(
        "--h_user_agent",
        help="Value for the h_User-Agent header for the proxy."
    )
    
    args = parser.parse_args()
    
    final_url_result = smart_encode_url_for_proxy_compress_base64(
        args.target_url,
        h_referer_val=args.h_referer,
        h_origin_val=args.h_origin,
        h_user_agent_val=args.h_user_agent
    )
    print(final_url_result)
