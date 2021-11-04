# youtube-dl MTV Act Concatenate

Tested on Fedora 34 & macOS Catalina + Big Sur + Monterey.

Prerequisites:

youtube-dl and ffmpeg (dnf install / brew install)



How to use:

Go to mtv.com and go copy the url of a desired show / episode.

Run this ruby script ***ruby mtv.rb*** and then paste in the url when it asks.

The program will handle the rest. Enjoy.

NOTE: This will work even with provider protected content, no credentials needed.


macOS users - known issue work-around:

The following file will need to be applied to your youtube-dl install (2021.6.6) if you are getting a error after entering the mtv url:

https://raw.githubusercontent.com/ytdl-org/youtube-dl/5e66c239a9e6d20044eac36b5982d3d39966091d/youtube_dl/extractor/mtv.py

In safari: right click, Save Page As...,  Save As: mtv, where: Downloads, Format: Page Source, Save

Open a terminal and copy + paste the following (or just move it into the directory manually)

cp ~/Downloads/mtv.txt /usr/local/Cellar/youtube-dl/2021.6.6/libexec/lib/python*/site-packages/youtube_dl/extractor/mtv.py
