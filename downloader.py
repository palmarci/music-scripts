import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from datetime import datetime
import shutil

current_dir = os.getcwd()

#TODO: add handler for ctrl+c to kill all processes and exit correctly

def check_dependencies():
    dependencies = ['yt-dlp', 'ffmpeg-normalize']
    missing_dependencies = []
    for dependency in dependencies:
        if not shutil.which(dependency):
            missing_dependencies.append(dependency)
    if missing_dependencies:
        print("The following dependencies are missing from the PATH:")
        for dependency in missing_dependencies:
            print(dependency)
        return False
    else:
        #print("All dependencies are available.")
        return True

def fix_file_name(name):
    to_remove = [' - Topic', '.', "'", ':', "/", '"']
    name = name.strip()
    for substring in to_remove:
        name = name.replace(substring, '')
    return name

def dl_single_video(video):
    to_check = ["title", "id", "uploader"]
    for c in to_check:
        if video.get(c) == None:
            print(f"ERROR: could not get video data for {video}")
            return

    print(f"working on: {video['title']} [{video['id']}] ...")
    temp_wav_file = fix_file_name(video["title"] + " - " + video["uploader"]) + ".wav"
    output_file = temp_wav_file.replace('.wav', '.mp3')

    if not os.path.exists(output_file):
        if not os.path.exists(temp_wav_file):
            dlCommand = f'yt-dlp --no-warnings -q -f bestaudio -o "{temp_wav_file}" --extract-audio --audio-format wav "https://www.youtube.com/watch?v={video["id"]}"'
            os.system(dlCommand)
        else:
            print(f'WARNING: not downloading temp wav file {temp_wav_file}, already exists...')

        #print(f"converting & normalizing {temp_wav_file} ...")
        fix_command = f'ffmpeg-normalize "{temp_wav_file}" --keep-loudness-range-target -nt ebu -t -9.5 -tp -0.1 -c:a libmp3lame -b:a 320k -o "{output_file}"'
        os.system(fix_command)
    else:
        print(f'WARNING: skipping output file {output_file}, already exists...')

    if not os.path.exists(output_file):
        print(f"ERROR: output file is not created: {output_file}")

    if os.path.isfile(temp_wav_file):
        os.remove(temp_wav_file)

def vid_list_from_playlist(url):
    playlistInfo = json.loads(subprocess.check_output(f'yt-dlp --no-warnings --dump-single-json --flat-playlist --playlist-end 1 "{url}"', shell=True, text=True))
    print(f'getting info for playlist {playlistInfo["title"]} ({playlistInfo["webpage_url"]})')

    if os.path.exists(os.path.join(current_dir, playlistInfo["title"])) == False:
        print("folder '" + playlistInfo["title"] + "' does not exist, creating...")
        os.mkdir(os.path.join(current_dir, playlistInfo["title"]))
    os.chdir(os.path.join(current_dir, playlistInfo["title"]))
   # videoList = []

#    try:
    print("extracting playlist data...")
    result = subprocess.check_output(f'yt-dlp --no-warnings --dump-single-json --flat-playlist "{url}"', shell=True, text=True)
    return json.loads(result)['entries']
    # return videos
    # for video in videos:
    #     videoList.append(video)
    # # except Exception as e:
    # #     print(f"Exception occurred: #{e}")
    # #     sys.exit(1)

    # return videoList

def vid_list_from_file(filepath):
    #TODO test this
    lines = []
    videos = []

    with open(filepath) as f:
        lines = [line.rstrip('\n') for line in f]
    folder_path = os.path.join(current_dir, datetime.now().strftime("%Y_%m_%d"))

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"folder '{folder_path}' created successfully!")

    for i in lines:
        result = json.loads(subprocess.check_output(f'yt-dlp --dump-json --no-warnings "https://www.youtube.com/watch?v={i}"', shell=True, text=True))
        videos.append(result)
        # TODO: maybe check the video vs the line count:
        # print(f'{len(videos)}/{len(lines)}')

    os.chdir(folder_path)
    return videos

def multithread_dl(list):
    num_threads = os.cpu_count() - 1 # so we dont freeze my pc
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(dl_single_video, list)

def main():
    parser = argparse.ArgumentParser(description="Download, convert and normalize a youtube playlist")
    parser.add_argument('--url', help='The playlist url')
    parser.add_argument('--file', type=str, help='Path to the video id list.')   
    args = parser.parse_args()

    os.chdir(current_dir)

    if (args.url == "" or args.url == None) and (args.file == "" or args.file == None):
        print("ERROR: you have to specify at least one input!\nRun --help for info.")
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    videos = []
    if args.url is not None and len(args.url) > 2:
        videos = vid_list_from_playlist(args.url)

    if args.file is not None and len(args.file) > 2:
        videos = vid_list_from_file(args.file)

    print(f"got {len(videos)} videos")
    print("switching to multithreaded download mode...")
    multithread_dl(videos)
    print("done")

if __name__ == "__main__":
    main()