from scipy.fft import fft
from scipy.io import wavfile
import argparse
import concurrent.futures
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os
import shutil
import sys
import tempfile

from utils import *
matplotlib.use('agg') # hacky fix: https://stackoverflow.com/a/74471578

# globals
TEMP_DIR = tempfile.mkdtemp()
DEBUG = False

def get_average_by_hertz_range(data_set, wanted_hz_beginning, wanted_hz_end, samples_per_hz):
	# Calculate the average of a range of Hz values in a dataset
	data = data_set[int(wanted_hz_beginning * samples_per_hz):int(wanted_hz_end * samples_per_hz)]
	final_cutoff = 0
	final_cutoff = sum(data) / len(data)
	return final_cutoff

def get_song_data(samp_freq, snd):
	# Get the time array and channel data from a sound file
	channel = snd[:, 0]
	time_array = np.arange(0, float(snd.shape[0]), 1)
	time_array = time_array / samp_freq
	time_array = time_array * 1000
	return time_array, channel

def get_cutoff(file_name, min_search_hz, hz_step, duration, downsample_size, original_filename):
	# Calculate the cutoff frequency of a sound file
	samp_freq, snd = wavfile.read(file_name)

	if snd.dtype == np.dtype('int16'):
		snd = snd / (2. ** 15)
	else:
		snd = snd / (2. ** 31)

	try:
		num_samples = int(samp_freq * duration)
		snd_middle = snd[num_samples // 2: num_samples // 2 + num_samples]

		freq_array, channel = get_song_data(samp_freq, snd_middle)

		p = np.abs(np.fft.fft(channel))
		p = p[:len(p) // 2]  # Take only the positive frequencies

		plotHzs = np.arange(0, len(p)) * (samp_freq / len(channel))
		plotDbs = 10 * np.log10(p)

		plotHzs = np.array(plotHzs)
		plotDbs = smooth_spectrum(np.array(plotDbs))

		downsampling_factor = len(plotHzs) // downsample_size
		plotHzs_downsampled = plotHzs[::downsampling_factor]
		plotDbs_downsampled = plotDbs[::downsampling_factor]

		plotHzs_downsampled = np.array(plotHzs_downsampled)
		plotDbs_downsampled = smooth_spectrum(np.array(plotDbs_downsampled))

		# Exclude the initial portion
		exclude_start_index = int(min_search_hz / hz_step)
		plotHzs_downsampled = plotHzs_downsampled[exclude_start_index:]
		plotDbs_downsampled = plotDbs_downsampled[exclude_start_index:]

		slopes = np.gradient(plotDbs_downsampled, plotHzs_downsampled)

		# Find the index of the point with the maximum negative slope
		valid_slope_indices = np.where(slopes < 0)[0]
		index_max_slope = valid_slope_indices[np.argmax(np.abs(slopes[valid_slope_indices]))]

		# Get the x-value at the index of the maximum slope
		x_max_slope = plotHzs_downsampled[index_max_slope]
	except Exception as e:
		logging.error(f'[{original_filename}] error while doing math: {e}')
		sys.exit(1)

	if DEBUG:
		plt.close()
		plt.plot(plotHzs, plotDbs, color="blue")
		plt.plot(plotHzs_downsampled, plotDbs_downsampled, color='r', linewidth=2)
		plt.xlabel('Frequency (Hz)')
		plt.ylabel('Power (dB)')
		plt.axvline(x=x_max_slope, color='g')
		plt.text(0, 0, os.path.basename(original_filename), fontsize=10)
		plt.savefig(TEMP_DIR + '/last_plot.png')
		plt.show()

	return x_max_slope

def smooth_spectrum(spectrum, window_size=11):
	window = np.hanning(window_size)
	smoothed = np.convolve(spectrum, window, mode='same') / sum(window)
	return smoothed

def process(file_name, args):
	original_file_name = file_name
	file_format = os.path.splitext(file_name)[1]
	wasnt_wav = None

	# convert if needed & get cutoff value
	if file_format != ".wav":
		temp_file_name = os.path.join(TEMP_DIR, get_file_hash(file_name) + '.wav')
		run_command(f'ffmpeg -y -nostats -loglevel panic -hide_banner -i "{file_name}" "{temp_file_name}"')
		file_name = temp_file_name
		wasnt_wav = True

	cutoff = get_cutoff(temp_file_name, args.min_search_hz, args.hz_step, args.duration, args.downsample_size, file_name)

	if wasnt_wav == True:
		os.remove(temp_file_name)
		
	mark = "✓" if cutoff >= args.accepted_hz else "✕"
	mark = f" {mark} "
	logging.info(f"{mark} {original_file_name} : {cutoff}")
	
	if args.action == "delete":
		logging.warning(f"deleting {original_file_name}")
		os.remove(original_file_name)

	if args.action == "rename":
		if cutoff <= args.accepted_hz:
			if '!' not in os.path.splitext(os.path.basename(original_file_name))[0]:
				new_file_name = os.path.dirname(original_file_name) + '/!' + os.path.splitext(os.path.basename(original_file_name))[0] + '_' + str(round(cutoff / 1000)) + "k" + file_format
				shutil.move(original_file_name, new_file_name)
				#logging.info(f"Renamed '{original_file_name}' to '{new_file_name}'")
			else:
				logging.warning(f'skipping rename: {original_file_name}, seems to be already renamed')

def main():
	global DEBUG
	# handle arguments
	parser = argparse.ArgumentParser(description="Analyse music files' quality in a given folder.")
	default_min_search_hz = 10000
	default_accepted_hz = 19500
	default_hz_step = 100
	default_duration = 60
	default_downsample_size = 200
	default_action = "rename"
	parser.add_argument('folder', help='The folder to search for audio files in')
	parser.add_argument('--min-search-hz', type=int, default=default_min_search_hz, help=f'Start the search from this frequency. (Default: {default_min_search_hz})')
	parser.add_argument('--accepted-hz', type=int, default=default_accepted_hz, help=f'The accepted cutoff frequency. We will accept these files and not throw warnings. (Default: {default_accepted_hz})')
	parser.add_argument('--hz-step', type=int, default=default_hz_step, help=f'The step size for frequency search (Default: {default_hz_step})')
	parser.add_argument('--duration', type=int, default=default_duration, help=f'Duration of the portion of the song to analyze in seconds (from the middle of the song) (Default: {default_duration})')
	parser.add_argument('--downsample-size', type=int, default=default_downsample_size, help=f'Size to use while downsampling (Default: {default_downsample_size})')
	parser.add_argument('--action', default=default_action, type=str, help=f'Action to do on the misbehaving song. Actions: nothing, rename or delete. (Default: {default_action})')
	parser.add_argument('--debug', action='store_true', help=f'Debug prints and graphs')
	args = parser.parse_args()

	# init
	check_dependencies("ffmpeg")
	DEBUG = args.debug
	setup_logging(DEBUG)
	
	# process user input
	if args.action == "delete":
		logging.warning("Files will be DELETED!")

	if not os.path.isdir(args.folder):
		logging.error("given folder not found!")
		sys.exit(1)

	if args.action not in ["nothing", "rename", "delete"]:
		logging.error("invalid action given in arguments!")
		sys.exit(1)

	# get files
	file_list = []
	for file in get_files_recursive(args.folder):
		file_format = os.path.splitext(file)[1]
		if is_audio_format(file):
			file_list.append(file)
	file_list.sort()
	logging.info(f"found {len(file_list)} audio files")

	# start multithreaded work
	cpu_count = get_thread_count(DEBUG)
	with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count) as executor:
		futures = []
		for f in file_list:
			future = executor.submit(process, f, args)
			futures.append(future)
		concurrent.futures.wait(futures) # wait for all tasks to complete
	os.removedirs(TEMP_DIR)
	logging.info("done, bye")

if __name__ == '__main__':
	main()