import argparse
import base64
import ipaddress
import urllib.parse
import zlib

# ---------------------------------------------------------------------------

def _valid_ip(value: str) -> str:
    """Argparse validator that raises if *value* is not an IPv4/6 address."""
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid IP address.")

def _encode(value: str) -> str:
    """Compress *value* with zlib and return url-safe base64 without '=' padding."""
    compressed = zlib.compress(value.encode('utf-8'))
    encoded = base64.urlsafe_b64encode(compressed).decode('utf-8')
    return encoded.rstrip('=')

def build_proxy_url(
    target_url: str,
    proxy_host: str = "127.0.0.1",
    h_referer: str | None = None,
    h_origin: str | None = None,
    h_user_agent: str | None = None,
    h_topembed: str | None = None,
) -> str:
    """Return the fully-formed URL that your proxy understands."""
    prefix = f"http://{proxy_host}:8888/proxy/m3u?url="

    # Encode primary url
    encoded_target = _encode(target_url)
    final_url = prefix + encoded_target

    # Collect optional h_ params in stable order
    h_params: list[tuple[str, str | None]] = [
        ("h_referer",    h_referer),
        ("h_origin",     h_origin),
        ("h_user_agent", h_user_agent),
        ("h_topembed",   h_topembed),
    ]

    for key, raw_val in h_params:
        if raw_val is None:
            continue
        encoded_val = _encode(raw_val)
        final_url += f"&{key}={encoded_val}"

    return final_url

# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compress + Base64 + prefix-encode a single URL for your proxy.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("target_url", help="Plain URL to encode (e.g. https://example.com/master.m3u8)")
    parser.add_argument("--proxy_host", default="127.0.0.1", type=_valid_ip,
                        help="Proxy host/IP to prepend in the final URL")
    parser.add_argument("--h_referer",    help="Value for h_referer query parameter")
    parser.add_argument("--h_origin",     help="Value for h_origin query parameter")
    parser.add_argument("--h_user_agent", help="Value for h_user_agent query parameter")
    parser.add_argument("--h_topembed",   help="Value for h_topembed query parameter (Topembed page URL)")

    args = parser.parse_args()

    proxy_url = build_proxy_url(
        args.target_url,
        proxy_host=args.proxy_host,
        h_referer=args.h_referer,
        h_origin=args.h_origin,
        h_user_agent=args.h_user_agent,
        h_topembed=args.h_topembed,
    )
    print(proxy_url)

if __name__ == "__main__":   # pragma: no cover
    main()
