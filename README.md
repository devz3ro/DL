pip3 install Flask requests beautifulsoup4 gunicorn

supply correct headers in headers.json file (referrer and origin)

2 separate scripts to encode urls:

1. encode_url.py will do a single url

Example:

`python3 encode_url.py https://google.com/
http://127.0.0.1:8888/proxy/m3u?url=https%3A%2F%2Fgoogle.com%2F`

2. encode_playlist.py will encode entire playlist

Example:

`cat test.m3u8
#EXTM3U
#EXTINF:-1 channel-number="1" tvg-id="" tvg-name="TEST" tvg-logo="" group-title="TEST",TEST
https://google.com/`

`python3 encode_playlist.py test.m3u8
Successfully processed 'test.m3u8' (3 lines read).
1 URLs/URIs were modified.
Output saved to 'test_encoded.m3u8'`

`cat test_encoded.m3u8
#EXTM3U
#EXTINF:-1 channel-number="1" tvg-id="" tvg-name="TEST" tvg-logo="" group-title="TEST",TEST
http://127.0.0.1:8888/proxy/m3u?url=https%3A%2F%2Fgoogle.com%2F`

enjoy.
