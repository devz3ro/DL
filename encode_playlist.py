import urllib.parse
import argparse
import os
import re
import base64
import zlib

PROXY_PREFIX = "http://127.0.0.1:8888/proxy/m3u?url="

def smart_encode_url_for_proxy_compress_base64(target_url, h_referer_val=None, h_origin_val=None, h_user_agent_val=None):
    if not target_url or not target_url.strip():
        return ""
        
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

def process_m3u8_file(input_filepath, output_filepath, cli_h_referer=None, cli_h_origin=None, cli_h_user_agent=None):
    lines_processed = 0
    urls_modified = 0

    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile, \
             open(output_filepath, 'w', encoding='utf-8') as outfile:

            for line in infile:
                lines_processed += 1
                stripped_line = line.strip()

                if not stripped_line:
                    outfile.write(line)
                    continue

                modified_line_content = None

                if stripped_line.startswith(("#EXT-X-KEY:", "#EXT-X-MEDIA:")):
                    match = re.match(r'(.*URI=")([^"]+)(".*)', stripped_line)
                    if match:
                        pre_uri_part = match.group(1)
                        original_uri = match.group(2)
                        post_uri_part = match.group(3)

                        if original_uri.strip():
                            new_uri = smart_encode_url_for_proxy_compress_base64(
                                original_uri, cli_h_referer, cli_h_origin, cli_h_user_agent
                            )
                            modified_line_content = f"{pre_uri_part}{new_uri}{post_uri_part}\n"
                            urls_modified += 1
                        else:
                            modified_line_content = line 
                    else:
                        modified_line_content = line
                
                elif stripped_line.startswith("#EXT-X-STREAM-INF:"):
                    uri_match = re.search(r'URI="([^"]+)"', stripped_line)
                    if uri_match:
                        original_uri = uri_match.group(1)
                        if original_uri.strip():
                            new_uri = smart_encode_url_for_proxy_compress_base64(
                                original_uri, cli_h_referer, cli_h_origin, cli_h_user_agent
                            )
                            modified_line_content = stripped_line.replace(original_uri, new_uri) + '\n'
                            urls_modified += 1
                        else:
                            modified_line_content = line
                    else:
                         modified_line_content = line


                elif stripped_line.startswith("#"):
                    modified_line_content = line
                else:
                    new_url = smart_encode_url_for_proxy_compress_base64(
                        stripped_line, cli_h_referer, cli_h_origin, cli_h_user_agent
                    )
                    if new_url:
                        modified_line_content = new_url + '\n'
                        urls_modified +=1
                    else:
                        modified_line_content = '\n'

                if modified_line_content is not None:
                    outfile.write(modified_line_content)
                else:
                    outfile.write(line)
        
        print(f"Successfully processed '{input_filepath}' ({lines_processed} lines read).")
        print(f"{urls_modified} URLs/URIs were modified.")
        print(f"Output saved to '{output_filepath}'")

    except FileNotFoundError:
        print(f"Error: Input file '{input_filepath}' not found.")
    except Exception as e:
        print(f"An error occurred during processing: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Processes an M3U8 file to compress, URL-safe Base64 encode, and prefix URLs/URIs within it, optionally adding h_ parameters.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_file",
        help="The path to the input M3U8 file (e.g., playlist.m3u8)."
    )
    parser.add_argument(
        "--h_referer",
        help="Value for the h_referer header to be added to proxied URLs."
    )
    parser.add_argument(
        "--h_origin",
        help="Value for the h_origin header to be added to proxied URLs."
    )
    parser.add_argument(
        "--h_user_agent",
        help="Value for the h_User-Agent header to be added to proxied URLs."
    )
    
    args = parser.parse_args()
    input_m3u8_file = args.input_file

    path_without_ext, original_ext = os.path.splitext(input_m3u8_file)
    output_m3u8_file = f"{path_without_ext}_encoded{original_ext}"

    if input_m3u8_file == output_m3u8_file:
        print(f"Error: Input and output filenames are the same ('{input_m3u8_file}').")
        print("Please rename your input file or choose a different naming scheme if it has '_encoded' already.")
    else:
        process_m3u8_file(
            input_m3u8_file, 
            output_m3u8_file,
            cli_h_referer=args.h_referer,
            cli_h_origin=args.h_origin,
            cli_h_user_agent=args.h_user_agent
        )
