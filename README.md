
# music-scripts
my python scripts for downloading, encoding and checking music

- downloader.py: downloads a youtube playlist with **yt-dlp**
- normalizer.py: extracts the encoded files with **ffmpeg**, analyzes them and also encodes them with **fdkaac** while checking them for quality info with **soxi** and the cutoff script
- cutoff.py: epic cutoff frequency analyzer with fast fourier transform
- plotMixBPM.py: draws the input file's BPM onto a graph
- mixDetect.py: loops trough an audio file and uses **songrec** to recognize songs 

please also note that the calculations are not perfect but they are good enough for me

https://github.com/yt-dlp/yt-dlp
https://github.com/marin-m/SongRec
https://github.com/noahgolmant/py-audio-analysis 
https://github.com/esonderegger/neg23 
https://github.com/scaperot/the-BPM-detector-python 
