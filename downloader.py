from datetime import datetime
import argparse
import concurrent.futures
import json
import logging
import os
import shutil
import subprocess
import sys

from utils import *

# globals (some will be filled by argparser)
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TARGET_TP = None
TARGET_LUFS = None
THREAD_COUNT = None
ERROR_COUNT = 0

def fix_file_name(name):
	to_remove = [' - Topic', '.', "'", ':', "/", '"']
	name = name.strip()
	for substring in to_remove:
		name = name.replace(substring, '')
	return name

def dl_single_video(video):
	global ERROR_COUNT
	# sanity check video data
	to_check = ["title", "id", "uploader"]
	for c in to_check:
		if video.get(c) == None:
			logging.error(f"could not get video data for {video}")
			return

	# define output file name
	logging.info(f"working on: {video['title']} [{video['id']}] ...")
	temp_wav_file = fix_file_name(video["title"] + " - " + video["uploader"]) + ".wav"
	output_file = temp_wav_file.replace('.wav', '.mp3')

	# handle file operations and start conversion
	if not os.path.exists(output_file):
		if not os.path.exists(temp_wav_file):
			dlCommand = f'yt-dlp --no-warnings -q -f bestaudio -o "{temp_wav_file}" --extract-audio --audio-format wav "https://www.youtube.com/watch?v={video["id"]}"'
			os.system(dlCommand)
		else:
			logging.warning(f'skipping download for "{temp_wav_file}", already exists...')
		status = normalize_to_mp3(temp_wav_file, output_file, TARGET_TP, TARGET_LUFS)
		if status != True:
			ERROR_COUNT += 1
			os.remove(output_file)
	else:
		logging.warning(f'skipping output file {output_file}, already exists...')

	# check and remove output files
	if not os.path.exists(output_file):
		logging.error(f"output file was not created: {output_file}")
		sys.exit(1)

	if os.path.isfile(temp_wav_file):
		os.remove(temp_wav_file)

def vid_list_from_playlist(url):
	playlistInfo = json.loads(subprocess.check_output(f'yt-dlp --no-warnings --dump-single-json --flat-playlist --playlist-end 1 "{url}"', shell=True, text=True))
	logging.info(f'getting info for playlist {playlistInfo["title"]} ({playlistInfo["webpage_url"]})')

	if os.path.exists(os.path.join(SCRIPT_DIR, playlistInfo["title"])) == False:
		logging.info("folder '" + playlistInfo["title"] + "' does not exist, creating...")
		os.mkdir(os.path.join(SCRIPT_DIR, playlistInfo["title"]))
	os.chdir(os.path.join(SCRIPT_DIR, playlistInfo["title"]))
	logging.info("extracting playlist data...")
	result = subprocess.check_output(f'yt-dlp --no-warnings --dump-single-json --flat-playlist "{url}"', shell=True, text=True)
	return json.loads(result)['entries']

def vid_list_from_file(filepath):
	lines = []
	videos = []

	with open(filepath) as f:
		lines = [line.rstrip('\n') for line in f]
	folder_path = os.path.join(SCRIPT_DIR, datetime.now().strftime("%Y_%m_%d"))

	if not os.path.exists(folder_path):
		os.makedirs(folder_path)
		logging.info(f"folder '{folder_path}' created successfully!")

	for i in lines:
		result = json.loads(subprocess.check_output(f'yt-dlp --dump-json --no-warnings "https://www.youtube.com/watch?v={i}"', shell=True, text=True))
		videos.append(result)
		# TODO:logging.info(f'{len(videos)}/{len(lines)}')

	os.chdir(folder_path)
	return videos

def multithread_dl(list):
	if THREAD_COUNT > 1:
		logging.info(f"switching to multithreaded download with {THREAD_COUNT} threads")
	with concurrent.futures.ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
		executor.map(dl_single_video, list)

def main():
	global TARGET_LUFS, TARGET_TP, THREAD_COUNT

	# handle arguments
	target_tp_default = -0.1
	target_lufs_default = -9.0
	parser = argparse.ArgumentParser(description="Download, convert and normalize a YouTube playlist")
	parser.add_argument('--url', help='The playlist url')
	parser.add_argument('--file', type=str, help='Path to the video id list.')   
	parser.add_argument('--target-tp', default=target_tp_default, help=f'Target maximum True Peak (default: {target_tp_default})')
	parser.add_argument('--target-lufs', default=target_lufs_default, help=f'LUFS target (default: {target_lufs_default})')
	parser.add_argument('--debug', action='store_true', help=f'Disables multithreading and enables debug prints.')
	parser.add_argument('--skip-normalization', action='store_true', help=f'Skips normalization alltogether.')
	args = parser.parse_args()

	# initialize stuff
	setup_logging(args.debug)
	THREAD_COUNT = get_thread_count(args.debug)
	check_dependencies(["ffmpeg", "yt-dlp"])
	TARGET_LUFS = float(args.target_lufs)
	TARGET_TP = float(args.target_tp)
	os.chdir(SCRIPT_DIR)

	# validate user input
	for i in [TARGET_LUFS, TARGET_TP]:
		if i > 0:
			logging.error(f"Target loudness values ({i}) can not be positive!")
			sys.exit(1)

	logging.info(f"Target TP = {TARGET_TP}")
	logging.info(f"Target LUFS = {TARGET_LUFS}")

	if (args.url is None) and (args.file is None):
		logging.error("You have to specify at least one input!\nRun --help for info.")
		sys.exit(1)

	if (args.url is not None) and (args.file is not None):
		logging.error("You specified both input types. I dont know what to do, check --help.")
		sys.exit(1)

	# get input videos
	videos = []
	if args.url is not None:
		videos = vid_list_from_playlist(args.url)
	elif args.file is not None:
		videos = vid_list_from_file(args.file)

	# start batch download
	logging.info(f"got {len(videos)} videos")
	multithread_dl(videos)
	logging.info(f"done with {ERROR_COUNT} errors, good bye...")

if __name__ == "__main__":
	main()