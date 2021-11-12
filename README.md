# music-scripts
my python scripts for downloading, encoding and checking music

what it does:
- downloads a youtube playlist
- extracts it with *ffmpeg*
- checks the file for quality (bitrate + **cutoff frequency**)
- then encodes it with *fdkaac* and renames it

i used some code from:
https://github.com/noahgolmant/py-audio-analysis
https://github.com/esonderegger/neg23
