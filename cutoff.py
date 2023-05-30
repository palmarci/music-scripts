from scipy.fft import fft
from scipy.io import wavfile
import argparse
import fnmatch
import hashlib
import matplotlib.pyplot as plt
import numpy as np
import os
import subprocess
import sys
import tempfile
import traceback

processed = 0
filecount = 0
debug = False
temp_dir = tempfile.mkdtemp()

def log(msg): 
	# dirty hack so we can redirect the output and tail -f the file
	print(msg, flush=True)

def run_command(command):
	# Execute a shell command and return the output as a string
	sub_process = subprocess.check_output(command, shell=True)
	return str(sub_process.decode('utf-8'))

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


def get_cutoff(file_name, min_search_hz, hz_step, duration, downsample_size, original_filename, accepted_hz):
	global processed
	# Calculate the cutoff frequency of a sound file
	samp_freq, snd = wavfile.read(file_name)

	if snd.dtype == np.dtype('int16'):
		snd = snd / (2. ** 15)
	else:
		snd = snd / (2. ** 31)

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
	


	plt.close()

	if x_max_slope >= accepted_hz:
		log(f"    [{processed}/{filecount}] - '{original_filename}': {x_max_slope}")
	else:
		log(f"!!! [{processed}/{filecount}] - '{original_filename}': {x_max_slope}")
		plt.figure(facecolor='red')




	plt.plot(plotHzs, plotDbs, color="blue")
	plt.plot(plotHzs_downsampled, plotDbs_downsampled, color='r', linewidth=2)
	plt.xlabel('Frequency (Hz)')
	plt.ylabel('Power (dB)')
	plt.axvline(x=x_max_slope, color='g')
	plt.text(0, 0, os.path.basename(original_filename), fontsize=10)


	processed += 1


	if debug:
		plt.savefig(temp_dir + '/last_plot.png')
	#	plt.show()

	plt.close()


	return


def smooth_spectrum(spectrum, window_size=11):
	window = np.hanning(window_size)
	smoothed = np.convolve(spectrum, window, mode='same') / sum(window)
	return smoothed

def get_file_hash(filename):
	# Calculate the MD5 hash of a file's name
	return hashlib.md5(filename.encode('utf-8')).hexdigest()

def is_audio_format(ext):
	# Check if a file extension corresponds to an audio format
	extensions = ['flac', 'alac', 'wav', 'aif', 'mp3', 'aac', 'm4a', 'webm', 'opus', 'ogg']
	ext = ext.replace(".", "")
	if ext in extensions:
		return True
	else:
		return False

def extract_files(directory, pattern):
	# Recursively extract files from a directory based on a pattern
	for root, dirs, files in os.walk(directory):
		for basename in files:
			if fnmatch.fnmatch(basename, pattern):
				file_name = os.path.join(root, basename)
				yield file_name

def process(file_name, args):
	cutoff = None
	file_format = os.path.splitext(file_name)[1]

	if file_format != ".wav":
		temp_file_name = os.path.join(temp_dir, get_file_hash(file_name) + '.wav')
		run_command(f'ffmpeg -y -nostats -loglevel panic -hide_banner -i "{file_name}" "{temp_file_name}"')
		cutoff = get_cutoff(temp_file_name, args.min_search_hz, args.hz_step, args.duration, args.downsample_size, file_name, args.accepted_hz)
		os.remove(temp_file_name)
	else:
		cutoff = get_cutoff(file_name, args.min_search_hz, args.hz_step, args.duration, args.downsample_size)


def main():
	global filecount, debug

	parser = argparse.ArgumentParser(description="Detect the cutoff frequency of audio files in a given directory.")

	parser.add_argument('folder', help='The folder to search for audio files in')
	parser.add_argument('--min-search-hz', type=int, default=10000, help='Start the search from this frequency.')
	parser.add_argument('--accepted-hz', type=int, default=19500, help='The accepted cutoff frequency. We will accept these files and not throw warnings.')
	parser.add_argument('--hz-step', type=int, default=100, help='The step size for frequency search in Hz')
	parser.add_argument('--duration', type=int, default=60, help='Duration of the portion of the song to analyze in seconds (from the middle of the song)')
	parser.add_argument('--downsample-size', type=int, default=200, help='Size to use while downsampling')
	parser.add_argument('--debug', type=bool, default=False, help='Set to true for debug prints and graphs')



	args = parser.parse_args()

	debug = args.debug

	file_list = []

	for file_name in extract_files(args.folder, '*'):
		file_format = os.path.splitext(file_name)[1]
		if is_audio_format(file_format):
			file_list.append(file_name)
		else:
			log(f"Skipping file {file_name}, as it is not an audio file.")
			continue

	file_list.sort()
	filecount = len(file_list)
	log(f'Found {filecount} audio files in the directory')

	for f in file_list:
		process(f, args)

if __name__ == '__main__':
	main()
