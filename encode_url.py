import urllib.parse
import argparse

PROXY_PREFIX = "http://127.0.0.1:8888/proxy/m3u?url="

def encode_and_prefix_url(url_to_encode):
    encoded_part = urllib.parse.quote(url_to_encode, safe='')
    return f"{PROXY_PREFIX}{encoded_part}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="URL encodes a given web URL and adds a prefix.")
    parser.add_argument("url", help="The web URL to encode and prefix.")
    args = parser.parse_args()
    input_url = args.url
    final_url_result = encode_and_prefix_url(input_url)
    print(final_url_result)
