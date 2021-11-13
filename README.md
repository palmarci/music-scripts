
# music-scripts
my python scripts for downloading, encoding and checking music

- downloader: downloads a youtube playlist with ~~youtube-dl~~ **yt-dlp** (to bypass throttling)
- normalizer: extracts the encoded files with **ffmpeg**, analyzes them and also encodes them with **fdkaac** while checking them for quality info with **soxi**
- cutoff: epic cutoff frequency analyzer
- plotMixBPM: draws the input file's BPM onto a graph


i used some code from: 
https://github.com/noahgolmant/py-audio-analysis 
https://github.com/esonderegger/neg23 
https://github.com/scaperot/the-BPM-detector-python 
