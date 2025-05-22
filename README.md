install prerequisites:  

pip3 install Flask requests beautifulsoup4 gunicorn

supply correct headers in headers.json file (referrer and origin)

*note* the headers.json file is *only* needed for a playlist that contains only "dl" mono urls.  
If you are using another provider, define the headers using the --h_referer, --h_origin, and --h_user_agent as shown in the examples below.  

(2 separate scripts provided to encode urls)  

-----------------------------------------------------------------------------------------------------------------------------------------------  

1. encode_url.py will encode a single url (now with optional headers)

Example:

python3 encode_url.py https://google.com/  
http://127.0.0.1:8888/proxy/m3u?url=eJzLKCkpKLbS10_Pz0_PSdVLzs_VBwBHIwbl

OR  

python3 encode_url.py https://google.com/ --h_referer "https://google.com/" --h_origin "https://foo.bar" --h_user_agent "MyCustomAgent/1.0"  
http://127.0.0.1:8888/proxy/m3u?url=eJzLKCkpKLbS10_Pz0_PSdVLzs_VBwBHIwbl&h_referer=eJzLKCkpKLbS10_Pz0_PSdVLzs_VBwBHIwbl&h_origin=eJzLKCkpKLbS10_Lz9dLSiwCACyYBXM&h_User-Agent=eJzzrXQuLS7Jz3VMT80r0TfUMwAAOlYF7w  

-----------------------------------------------------------------------------------------------------------------------------------------------  

2. encode_playlist.py will encode an entire playlist (now with optional headers)  

Example:  

cat test.m3u8  
#EXTM3U  
#EXTINF:-1 channel-number="1" tvg-id="" tvg-name="TEST" tvg-logo="" group-title="TEST",TEST  
https://google.com/

python3 encode_playlist.py test.m3u8  
Successfully processed 'test.m3u8' (3 lines read).  
1 URLs/URIs were modified.  
Output saved to 'test_encoded.m3u8'  

cat test_encoded.m3u8  
#EXTM3U  
#EXTINF:-1 channel-number="1" tvg-id="" tvg-name="TEST" tvg-logo="" group-title="TEST",TEST  
http://127.0.0.1:8888/proxy/m3u?url=eJzLKCkpKLbS10_Pz0_PSdVLzs_VBwBHIwbl  

OR  

python3 encode_playlist.py test.m3u8 --h_referer "https://google.com/" --h_origin "https://foo.bar" --h_user_agent "MyCustomAgent/1.0"  
Successfully processed 'test.m3u8' (3 lines read).  
1 URLs/URIs were modified.  
Output saved to 'test_encoded.m3u8'  

cat test_encoded.m3u8  
#EXTM3U  
#EXTINF:-1 channel-number="1" tvg-id="" tvg-name="TEST" tvg-logo="" group-title="TEST",TEST  
http://127.0.0.1:8888/proxy/m3u?url=eJzLKCkpKLbS10_Pz0_PSdVLzs_VBwBHIwbl&h_referer=eJzLKCkpKLbS10_Pz0_PSdVLzs_VBwBHIwbl&h_origin=eJzLKCkpKLbS10_Lz9dLSiwCACyYBXM&h_User-Agent=eJzzrXQuLS7Jz3VMT80r0TfUMwAAOlYF7w  

-----------------------------------------------------------------------------------------------------------------------------------------------  

Run app:

gunicorn --workers 4 --bind 0.0.0.0:8888 dl:dl

enjoy.
