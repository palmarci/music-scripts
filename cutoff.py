import argparse
import hashlib
import os
import sys
import subprocess
import fnmatch
import numpy as np
from scipy.fft import fft
from scipy.io import wavfile
import tempfile
import matplotlib.pyplot as plt
import traceback

processed = 0
filecount = 0
debug = False
temp_dir = tempfile.mkdtemp()

def run_command(command):
	# Execute a shell command and return the output as a string
	sub_process = subprocess.check_output(command, shell=True)
	return str(sub_process.decode('utf-8'))

def get_average_by_hertz_range(data_set, wanted_hz_beginning, wanted_hz_end, samples_per_hz):
	# Calculate the average of a range of Hz values in a dataset
	data = data_set[int(wanted_hz_beginning * samples_per_hz):int(wanted_hz_end * samples_per_hz)]
	final_cutoff = 0
	try:
		final_cutoff = sum(data) / len(data)
	except Exception as e:
		print("\nERROR:")
		print(data, wanted_hz_beginning, wanted_hz_end, samples_per_hz)
		print(e)
		print(f"{traceback.format_exc()}")
	return final_cutoff

def get_song_data(samp_freq, snd):
	# Get the time array and channel data from a sound file
	channel = snd[:, 0]
	time_array = np.arange(0, float(snd.shape[0]), 1)
	time_array = time_array / samp_freq
	time_array = time_array * 1000
	return time_array, channel

def get_cutoff(file_name, min_search_hz, max_search_hz, hz_step, duration):
	# Calculate the cutoff frequency of a sound file
	samp_freq, snd = wavfile.read(file_name)

	if snd.dtype == np.dtype('int16'):
		snd = snd / (2. ** 15)
	else:
		snd = snd / (2. ** 31)

	num_samples = int(samp_freq * duration)
	snd_middle = snd[num_samples // 2 : num_samples // 2 + num_samples]

	time_array, channel = get_song_data(samp_freq, snd_middle)
	num_sample_points = len(channel)

	p = fft(channel)

	n_unique_pts = np.ceil((num_sample_points + 1) / 2.0)
	p = p[0:int(n_unique_pts)]

	p = np.abs(p)
	p = p / float(num_sample_points)
	p = p ** 2

	if num_sample_points % 2 > 0:
		p[1:len(p)] = p[1:len(p)] * 2
	else:
		p[1:len(p) - 1] = p[1:len(p) - 1] * 2

	freq_array = np.arange(0, n_unique_pts, 1.0) * (samp_freq / num_sample_points)

	plotHzs = []
	plotDbs = []

	samples_per_hz = 1 / (samp_freq / num_sample_points)

	for i in range(min_search_hz, max_search_hz, hz_step):
		current_avg = get_average_by_hertz_range(10 * np.log10(p), i - hz_step / 2, i + hz_step / 2, samples_per_hz)
		plotHzs.append(i)
		plotDbs.append(current_avg)


	fall_points = []
	inclinations = []
	average_power = np.mean(plotDbs)

	for i in range(len(plotDbs) - 1):
		if plotDbs[i] > plotDbs[i + 1]:
			fall_points.append(plotHzs[i + 1])
			inclination = plotDbs[i] - plotDbs[i + 1]
			inclinations.append(inclination)

	if debug:
		for i in range(len(fall_points)):
			print(f'{fall_points[i]}: {inclinations[i]}')

	
	current_cutoff_hz = fall_points[inclinations.index(max(inclinations))]
	current_cutoff_pwr = plotDbs[plotHzs.index(current_cutoff_hz)]

	accepted_cutoff_hz = min(plotHzs, key=lambda x:abs(x-max_search_hz))
	accepted_cutoff_power = plotDbs[plotHzs.index(accepted_cutoff_hz)]

	final_cutoff = 0.0

	if current_cutoff_hz <= (accepted_cutoff_hz - 500): # due to the fact that i cant code
		
		threshold_pwr = max(plotDbs) * 1.30 # magic number lol
		
		if debug:
			print(f'current cutoff: {current_cutoff_hz} hz @ {current_cutoff_pwr}, accepted cuttoff {accepted_cutoff_hz} hz @ {accepted_cutoff_power}')
			print(f'threshold: {threshold_pwr} <=?  accepted: {accepted_cutoff_power}')

		if  threshold_pwr <= accepted_cutoff_power:
			final_cutoff = accepted_cutoff_hz
		else:
			final_cutoff = current_cutoff_hz
	else:
		final_cutoff = current_cutoff_hz

	if debug:
		plt.plot(plotHzs, plotDbs)
		plt.xlabel('Frequency (Hz)')
		plt.ylabel('Power (dB)')
		plt.axvline(x=final_cutoff, color='r')
		plt.show()

	return final_cutoff

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
	global processed
	cutoff = None
	file_format = os.path.splitext(file_name)[1]

	#args.max_search_hz += 1000 # hack

	if file_format != ".wav":
		temp_file_name = os.path.join(temp_dir, get_file_hash(file_name) + '.wav')
		run_command(f'ffmpeg -y -nostats -loglevel panic -hide_banner -i "{file_name}" "{temp_file_name}"')
		cutoff = get_cutoff(temp_file_name, args.min_search_hz, args.max_search_hz, args.hz_step, args.duration)
		os.remove(temp_file_name)
	else:
		cutoff = get_cutoff(file_name, args.min_search_hz, args.max_search_hz, args.hz_step, args.duration)

	processed += 1

	if cutoff >= 19000:
		print(f"    [{processed}/{filecount}] - '{file_name}': {cutoff}")
	else:
		print(f"!!! [{processed}/{filecount}] - '{file_name}': {cutoff}")

def main():
	global filecount, debug

	parser = argparse.ArgumentParser(description="Detect the cutoff frequency of audio files in a given directory.")

	parser.add_argument('folder', help='The folder to search for audio files')
	parser.add_argument('--min-search-hz', type=int, default=10000, help='The minimum search frequency in Hz')
	parser.add_argument('--max-search-hz', type=int, default=20000, help='The maximum search frequency in Hz')
	parser.add_argument('--hz-step', type=int, default=100, help='The step size for frequency search in Hz')
	parser.add_argument('--debug', type=bool, default=False, help='Plot debug graph')
	parser.add_argument('--duration', type=int, default=60, help='Duration of the portion of the song to analyze in seconds')


	args = parser.parse_args()

	debug = args.debug

	file_list = []

	for file_name in extract_files(args.folder, '*'):
		file_format = os.path.splitext(file_name)[1]
		if is_audio_format(file_format):
			file_list.append(file_name)
		else:
			print(f"Skipping file {file_name}, as it is not an audio file.")
			continue

	file_list.sort()
	filecount = len(file_list)
	print(f'Found {filecount} audio files in the directory')

	for f in file_list:
		process(f, args)

if __name__ == '__main__':
	main()
