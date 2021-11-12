# music-scripts
my python scripts for downloading, encoding and checking music

what it does:
- downloads a youtube playlist with *yt-dlp*
- extracts the encoded files with *ffmpeg*
- checks them for quality with *sox/soxi* (bitrate + **epic cutoff frequency analyzer**)
- then encodes the files with *fdkaac* and also renames them


i used some code from:

https://github.com/noahgolmant/py-audio-analysis

https://github.com/esonderegger/neg23
