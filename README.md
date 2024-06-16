
# music-scripts
<u>my scripts for downloading, encoding and checking music</u>

- [music-scripts](#music-scripts)
    - [requirements](#requirements)
    - [scripts](#scripts)
    - [other interesting tools](#other-interesting-tools)
    - [thanks to](#thanks-to)
    - [TODOs](#todos)


>please also note that the scripts & calculations are not perfect but they are good enough for me

### requirements

these tools must be in in your path:
- yt-dlp
- ffmpeg
- songrec

### scripts

- **downloader.py**: downloads a list of videos from youtube (either from a playlist or a .txt file), normalizes and converts them
- **folder_cutoff.py**: analyses a folder full of music and prints their cutoff frequency. it is mainly used to determine the files' quality, but can be also used to rename or delete them accordingly
- **mix_plot_bpm.py**: draws the input mix file's BPM onto a graph, useful for viewing the DJ set's tempo over time
- **mix_detect.py**: loops trough a long audio file and recognizes the songs in it using the <code>songrec</code> tool (Shazam API) 
- **rb_mix_converter.py**: converts every wav file in a given folder to MP3 based on the file date tags, mainly used via <code>rekordbox</code>
- **ytmusic_batch_search.py**: searches and returnes a YT Music link for every line in a given file


### other interesting tools
- <https://codeberg.org/derat/soundalike>: great tool for de-duplicating your music library
- <https://github.com/slhck/ffmpeg-normalize>:  cool wrapper for ffmpeg
  
### thanks to
- https://github.com/yt-dlp/yt-dlp
- https://github.com/marin-m/SongRec
- https://github.com/noahgolmant/py-audio-analysis 
- https://github.com/esonderegger/neg23 
- https://github.com/scaperot/the-BPM-detector-python 
- https://github.com/slhck/ffmpeg-normalize


### TODOs
- add yt-dlp playlist caller .bat file for dummies
- refactor common code to utils file
- check back dynamic mode ffmpeg warning
- downloader.py: vid_list_from_file: test functionality, check back line count vs video count
- folder_cutoff.py: rework