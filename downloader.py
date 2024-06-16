from datetime import datetime
import argparse
import concurrent.futures
import json
import logging
import os
import shutil
import subprocess
import sys

# configurable parameteres
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TARGET_LUFS = -8.0
TARGET_TP = -0.1
DEBUG_MODE = False

def check_dependencies():
	dependencies = ['yt-dlp', 'ffmpeg']
	for dependency in dependencies:
		if not shutil.which(dependency):
			logging.error(f"Missing from PATH: {dependency}")
			sys.exit(1)

def fix_file_name(name):
	to_remove = [' - Topic', '.', "'", ':', "/", '"']
	name = name.strip()
	for substring in to_remove:
		name = name.replace(substring, '')
	return name

def normalize(input_wav, output_mp3):
	# analyze the file with ffmpeg
	analyze_command = (
		f"ffmpeg -i '{input_wav}' -af loudnorm=print_format=json -f null - 2>&1"
	)
	result = subprocess.run(analyze_command, shell=True, capture_output=True, text=True)
	analysis_output = result.stdout
	start_idx = analysis_output.find('{')
	end_idx = analysis_output.rfind('}') + 1
	analysis_json = analysis_output[start_idx:end_idx]
	analysis_data = json.loads(analysis_json)
	logging.debug(f"analysis_data for {input_wav}: {analysis_data}")

	# extract the measured values
	input_i = float(analysis_data["input_i"])
	input_tp = float(analysis_data["input_tp"])
	input_lra = float(analysis_data["input_lra"])
	input_thresh = float(analysis_data["input_thresh"])

	# calculate the required gain
	required_gain = TARGET_LUFS - input_i
	actual_target = None

	# determine if achieving the target loudness is possible without clipping
	if input_tp + required_gain > TARGET_TP:
		max_possible_gain = TARGET_TP - input_tp
		adjusted_lufs = input_i + max_possible_gain
		logging.warning(f"Target LUFS of {TARGET_LUFS} is not possible. Adjusting to {adjusted_lufs} LUFS to avoid clipping.")
		actual_target = adjusted_lufs
	else:
		actual_target = TARGET_LUFS
	logging.debug(f"running with {actual_target} LUFS target ")

	# normalize & convert to mp3
	normalize_command = (
		f"ffmpeg -i '{input_wav}' "
		f"-af loudnorm=I={actual_target}:TP={TARGET_TP}:LRA={input_lra}:linear=true:"
		f"measured_I={input_i}:measured_TP={input_tp}:"
		f"measured_LRA={input_lra}:measured_thresh={input_thresh} "
		f"-c:a libmp3lame -b:a 320k '{output_mp3}'"
	)
	logging.debug(normalize_command)
	result = subprocess.run(normalize_command, shell=True, capture_output=True, text=True)

def dl_single_video(video):
	# sanity check video data
	to_check = ["title", "id", "uploader"]
	for c in to_check:
		if video.get(c) == None:
			logging.error(f"could not get video data for {video}")
			return

	# define output file name
	logging.info(f"downloading: {video['title']} [{video['id']}] ...")
	temp_wav_file = fix_file_name(video["title"] + " - " + video["uploader"]) + ".wav"
	output_file = temp_wav_file.replace('.wav', '.mp3')

	# handle file operations and start conversion
	if not os.path.exists(output_file):
		if not os.path.exists(temp_wav_file):
			dlCommand = f'yt-dlp --no-warnings -q -f bestaudio -o "{temp_wav_file}" --extract-audio --audio-format wav "https://www.youtube.com/watch?v={video["id"]}"'
			os.system(dlCommand)
		else:
			logging.warning(f'skipping download for "{temp_wav_file}", already exists...')
		logging.info(f"normalizing: {video['title']} [{video['id']}] ...")
		normalize(temp_wav_file, output_file)
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
   	# videoList = []
	# try:
	logging.info("extracting playlist data...")
	result = subprocess.check_output(f'yt-dlp --no-warnings --dump-single-json --flat-playlist "{url}"', shell=True, text=True)
	return json.loads(result)['entries']
	# return videos
	# for video in videos:
	#     videoList.append(video)
	# # except Exception as e:
	# #     logging.info(f"Exception occurred: #{e}")
	# #     sys.exit(1)

	# return videoList

def vid_list_from_file(filepath):
	#TODO test this
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
		# TODO: maybe check the video vs the line count:
		# logging.info(f'{len(videos)}/{len(lines)}')

	os.chdir(folder_path)
	return videos

def multithread_dl(list):
	num_threads = os.cpu_count() - 1 # so we dont freeze my pc
	if num_threads > 8:
		num_threads = 8
	logging.info(f"switching to multithreaded download with {num_threads} threads")

	with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
		try:
			executor.map(dl_single_video, list)
		except KeyboardInterrupt:
			logging.warning("got ctrl+c event, force shutting down!")
			executor.shutdown(wait=False)

def setup_logging():
	target_level = logging.DEBUG if DEBUG_MODE else logging.INFO
	logging.basicConfig(
		level=target_level,
		format='%(asctime)s - %(levelname)s - %(message)s',
		handlers=[
			logging.StreamHandler(sys.stdout)
		]
	)
	return

def main():
	parser = argparse.ArgumentParser(description="Download, convert and normalize a YouTube playlist")
	parser.add_argument('--url', help='The playlist url')
	parser.add_argument('--file', type=str, help='Path to the video id list.')   
	args = parser.parse_args()

	# init
	setup_logging()
	os.chdir(SCRIPT_DIR)

	# check arguments and dependencies
	if (args.url is None) and (args.file is None):
		logging.error("You have to specify at least one input!\nRun --help for info.")
		sys.exit(1)

	if (args.url is not None) and (args.file is not None):
		logging.error("You specified both input types. I dont know what to do...")
		sys.exit(1)

	check_dependencies()

	# get input videos
	videos = []
	if args.url is not None:
		videos = vid_list_from_playlist(args.url)
	elif args.file is not None:
		videos = vid_list_from_file(args.file)

	# start batch download
	logging.info(f"got {len(videos)} videos")
	multithread_dl(videos)
	logging.info("all downloads are done, bye...")

if __name__ == "__main__":
	main()