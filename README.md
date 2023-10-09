
# music-scripts
my python scripts for downloading, encoding and checking music

must be in path: ffmpeg-normalize, yt-dlp, ffmpeg, songrec

- downloader.py: downloads a youtube playlist and normalizes the output files
- folder_normalizer.py: normalizes the files' loudness in a given folder
- folder_cutoff.py: analyses a folder full of music files and prints their cutoff frequency. it is mainly used to determine the files' quality
- mix_plot_bpm.py: draws the input file's BPM onto a graph
- mix_detect.py: loops trough a long audio file and recognizes songs using the shazam api 
- rb_mix_converter.py: converts every wav file in a given folder to mp3
- ytmusic_batch_search.py: searches and returnes a YT Music link for every line in a given file

please also note that the scripts & calculations are not perfect but they are good enough for me
also check out this great project to filter out duplicated music: https://codeberg.org/derat/soundalike

big thanks to:
- https://github.com/yt-dlp/yt-dlp
- https://github.com/marin-m/SongRec
- https://github.com/noahgolmant/py-audio-analysis 
- https://github.com/esonderegger/neg23 
- https://github.com/scaperot/the-BPM-detector-python 
- https://github.com/slhck/ffmpeg-normalize
