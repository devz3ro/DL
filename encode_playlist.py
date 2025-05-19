import urllib.parse
import argparse
import os
import re

PROXY_PREFIX = "http://127.0.0.1:8888/proxy/m3u?url="

def encode_and_prefix_url(url_to_process):
    trimmed_url = url_to_process.strip()
    if not trimmed_url:
        return ""

    encoded_url = urllib.parse.quote(trimmed_url, safe='')
    return f"{PROXY_PREFIX}{encoded_url}"

def process_m3u8_file(input_filepath, output_filepath):
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
                            new_uri = encode_and_prefix_url(original_uri)
                            modified_line_content = f"{pre_uri_part}{new_uri}{post_uri_part}\n"
                            urls_modified += 1
                        else:
                            modified_line_content = line
                    else:
                        modified_line_content = line

                elif stripped_line.startswith("#"):
                    modified_line_content = line
                else:
                    new_url = encode_and_prefix_url(stripped_line)
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
        description="Processes an M3U8 file to URL-encode and prefix URLs/URIs within it.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_file",
        help="The path to the input M3U8 file (e.g., playlist.m3u8)."
    )

    args = parser.parse_args()
    input_m3u8_file = args.input_file

    path_without_ext, original_ext = os.path.splitext(input_m3u8_file)
    output_m3u8_file = f"{path_without_ext}_encoded{original_ext}"

    if input_m3u8_file == output_m3u8_file:
        print(f"Error: Input and output filenames are the same ('{input_m3u8_file}').")
        print("Please rename your input file or choose a different naming scheme if it has '_encoded' already.")
    else:
        process_m3u8_file(input_m3u8_file, output_m3u8_file)
