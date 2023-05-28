import argparse
import hashlib
import os
import sys
import subprocess
from multiprocessing import Pool, Manager, Lock
import fnmatch
import numpy as np
from scipy.fft import fft
from scipy.io import wavfile
import tempfile
import matplotlib.pyplot as plt

processed = 0
temp_dir = tempfile.mkdtemp()
lock = Lock()

def run_command(command):
	sub_process = subprocess.check_output(command, shell=True)
	return str(sub_process.decode('utf-8'))

def get_average_by_hertz_range(data_set, wanted_hz_beginning, wanted_hz_end, samples_per_hz):
	data = data_set[int(wanted_hz_beginning * samples_per_hz):int(wanted_hz_end * samples_per_hz)]
	return sum(data) / len(data)

def get_song_data(samp_freq, snd):
	channel = snd[:, 0]
	time_array = np.arange(0, float(snd.shape[0]), 1)

	time_array = time_array / samp_freq
	time_array = time_array * 1000

	return time_array, channel

def get_cutoff(file_name, min_search_hz, max_search_hz, hz_step, hz_range):
	samp_freq, snd = wavfile.read(file_name)

	if snd.dtype == np.dtype('int16'):
		snd = snd / (2. ** 15)
	else:
		snd = snd / (2. ** 31)

	time_array, channel = get_song_data(samp_freq, snd)
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
		plotHzs.append([i])
		plotDbs.append(current_avg)

	top = max(plotDbs)
	bot = min(plotDbs)
	avgs = []
	low_end = []

	for i in plotDbs:
		avgs.append(((i / top) * 100) - 100)

	worst = max(avgs)

	i = 0
	while i < len(avgs):
		if avgs[i] - hz_range / 2 < worst and worst < avgs[i] + hz_range / 2:
			low_end.append(i)
		i = i + 1

	cutoff = plotHzs[(low_end[0] - 1)][0]

	return cutoff

def get_file_hash(filename):
	return hashlib.md5(filename.encode('utf-8')).hexdigest()

def is_audio_format(ext):
	extensions = ['3gp', '8svx', 'aa', 'aac', 'aax', 'act', 'aiff', 'alac', 'amr', 'ape', 'au', 'awb', 'cda', 'dss',
				  'dvf', 'flac', 'gsm', 'iklax', 'ivs', 'm4a', 'm4b', 'm4p', 'mmf', 'mogg', 'mp3', 'mpc', 'msv', 'nmf',
				  'oga', 'ogg', 'opus', 'ra', 'raw', 'rf64', 'rm', 'sln', 'tta', 'voc', 'vox', 'wav', 'webm', 'wma',
				  'wv']
	ext = ext.replace(".", "")
	if ext in extensions:
		return True
	else:
		return False

def extract_files(directory, pattern):
	for root, dirs, files in os.walk(directory):
		for basename in files:
			if fnmatch.fnmatch(basename, pattern):
				file_name = os.path.join(root, basename)
				yield file_name

def process(file_name, min_search_hz, max_search_hz, hz_step, hz_range, filecount, processed):
	cutoff = None
	file_format = os.path.splitext(file_name)[1]

	if file_format != ".wav":        
		temp_file_name = os.path.join(temp_dir, get_file_hash(file_name) + '.wav')
		run_command(f'ffmpeg -y -nostats -loglevel panic -hide_banner -i "{file_name}" "{temp_file_name}"')
		cutoff = get_cutoff(temp_file_name, min_search_hz, max_search_hz, hz_step, hz_range)
		os.remove(temp_file_name)
	else:
		cutoff = get_cutoff(file_name, min_search_hz, max_search_hz, hz_step, hz_range)

	with lock:
		processed.value += 1
		current_processed = processed.value

	if cutoff >= 20000:
		print(f"    [{current_processed}/{filecount.value}] - {file_name}: {cutoff}")
	else:
		print(f"!!! [{current_processed}/{filecount.value}] - {file_name}: {cutoff}")

def main():
	manager = Manager()
	filecount = manager.Value('i', 0)
	processed = manager.Value('i', 0)

	parser = argparse.ArgumentParser(description="""Detect the cutoff frequency of audio files in a given directory.
		\r\n
		WARNING: high CPU and memory usage. Subprocesses can get killed by the kernel if the system is out of memory. 
		It is highly recommended to have swap space, otherwise the script may hang and not exit properly, waiting for the dead subprocesses. 
		If the issue persists, you may need to lower the number of threads or investigate if there is a memory leak.""")

	parser.add_argument('folder', help='The folder to search for audio files')
	parser.add_argument('--min-search-hz', type=int, default=10000, help='The minimum search frequency in Hz')
	parser.add_argument('--max-search-hz', type=int, default=24000, help='The maximum search frequency in Hz')
	parser.add_argument('--hz-step', type=int, default=500, help='The step size for frequency search in Hz')
	parser.add_argument('--hz-range', type=int, default=12, help='The range of frequencies to consider in Hz')

	args = parser.parse_args()

	cpu = os.cpu_count()
	if cpu >= 8:
		cpu = cpu -2
	else:
		cpu = cpu -1 

	print(f'Starting with {cpu} threads')
	pool = Pool(processes=cpu)

	file_list = []

	for file_name in extract_files(args.folder, '*'):
		file_format = os.path.splitext(file_name)[1]
		if is_audio_format(file_format):
			file_list.append(file_name)
		else:
			print(f"Skipping file {file_name}, as it is not an audio file.")
			continue

	filecount.value = len(file_list)
	print(f'Found {filecount.value} audio files in the directory')

	pool.starmap(process, [(file_name, args.min_search_hz, args.max_search_hz, args.hz_step, args.hz_range, filecount, processed)
						   for file_name in file_list])

if __name__ == '__main__':
	main()
