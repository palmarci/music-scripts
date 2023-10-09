import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from datetime import datetime

from yt_dlp import YoutubeDL

current_dir = os.getcwd()
ytdl = YoutubeDL({'quiet': False, 'verbose': False, 'ignoreerrors': True})

def fix_file_name(name):
	name = name.strip()
	name = name.replace(' - Topic', '').replace('.', '').replace("'", '').replace(':', '').replace("/", "").replace('"', '')
	return name

def dl_single_video(video):
	if video is None or video['title'] is None or video["id"] is None:
		return

	print(f"{video['title']} - [{video['id']}]")
	dlFileName = fix_file_name(video["title"] + " - " + video["uploader"]) + ".wav"
	output = dlFileName.replace('.wav', '.mp3')

	if not os.path.exists(output):
		if not os.path.exists(dlFileName):
			dlCommand = f'yt-dlp -q -f bestaudio -o "{dlFileName}" --extract-audio --audio-format wav "https://www.youtube.com/watch?v={video["id"]}"'
			os.system(dlCommand)
		else:
			print(f'not downloading file {dlFileName}, already exists...')

		applyCommand = f'ffmpeg-normalize "{dlFileName}" --keep-loudness-range-target -nt ebu -t -9.5 -tp -0.1 -c:a libmp3lame -b:a 320k -o "{output}"'
		os.system(applyCommand)
	else:
		print(f'SKIPPING! file {dlFileName}, already exists...')

	if not os.path.exists(output):
		print(f"error: output file is not created: {output}")
		sys.exit(1)

	if os.path.isfile(dlFileName):
		os.remove(dlFileName)

def vid_list_from_playlist(url):
	playlistInfo = json.loads(subprocess.check_output(f'yt-dlp --no-warnings --dump-single-json --flat-playlist --playlist-end 1 "{url}"', shell=True, text=True))
	print(f'{playlistInfo["title"]}: [{playlistInfo["webpage_url"]}]')

	if os.path.exists(os.path.join(current_dir, playlistInfo["title"])) == False:
		print("folder '" + playlistInfo["title"] + "' does not exist, creating...")
		os.mkdir(os.path.join(current_dir, playlistInfo["title"]))
	os.chdir(os.path.join(current_dir, playlistInfo["title"]))
	videoList = []

	with ytdl:
		try:
			result = ytdl.extract_info(url, download=False)
		except Exception as e:
			print(f"fail: #{e}")
			sys.exit(1)

		if 'entries' in result:
			videos = result['entries']

			for video in videos:
				videoList.append(video)

			fullSize = len(result['entries'])
			print(f"got {len(videoList)} / {fullSize} videos")
	return videoList

def vid_list_from_file(filepath):
	lines = []
	videos = []

	with open(filepath) as f:
		lines = [line.rstrip('\n') for line in f]
	folder_path = os.path.join(current_dir, datetime.now().strftime("%Y_%m_%d"))

	if not os.path.exists(folder_path):
		os.makedirs(folder_path)
		print(f"Folder '{folder_path}' created successfully!")

	for i in lines:
		result = ytdl.extract_info(f'https://www.youtube.com/watch?v={i}', download=False)
		videos.append(result)
		print(f'{len(videos)}/{len(lines)}')

	os.chdir(folder_path)
	return videos

def multithread_dl(list):
	num_threads = os.cpu_count() - 1 # so we dont freeze my os
	with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
		executor.map(dl_single_video, list)

def main():
	parser = argparse.ArgumentParser(description="Download, convert and normalize a youtube playlist")
	parser.add_argument('--url', help='The playlist url')
	parser.add_argument('--file', type=str, help='Path to the video id list.')	
	args = parser.parse_args()

	os.chdir(current_dir)

	if (args.url == "" or args.url == None) and (args.file == "" or args.file == None):
		print("Error: you have to specify at least one input!\nRun --help for info.")
		sys.exit(1)

	videos = []
	if args.url is not None and len(args.url) > 2:
		videos = vid_list_from_playlist(args.url)

	if args.file is not None and len(args.file) > 2:
		videos = vid_list_from_file(args.file)
	
	print("switching to multihreaded mode...")
	multithread_dl(videos)


if __name__ == "__main__":
	main()