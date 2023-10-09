import array
import math
import wave
import subprocess
import matplotlib.pyplot as plt
import numpy
import pywt
from scipy import signal
import sys
import os
import argparse
import shutil
import subprocess
import tempfile

def convertToWav(input_file, output_dir):
	print("converting to wav...")
	temp_dir = tempfile.mkdtemp(dir=output_dir)
	output_file = os.path.join(temp_dir, "output.wav")
	ffmpeg_command = f'ffmpeg -loglevel quiet -n -i "{input_file}" "{output_file}"'
	subprocess.call(ffmpeg_command, shell=True)
	return output_file


def formatSeconds(seconds):
	hours = seconds // (60*60)
	seconds %= (60*60)
	minutes = seconds // 60
	seconds %= 60
	return "%02i:%02i:%02i" % (hours, minutes, seconds)

def read_wav(filename, startSecond, endSecond):
	try:
		wf = wave.open(filename, "rb")
		nsamps = wf.getnframes()
		fs = wf.getframerate()

		if nsamps == 0 or fs == 0:
			print(f"[E] while getting basic wav data")
			sys.exit(1)

		startSample = fs * startSecond
		endSample = fs * endSecond
		samplesToRead = endSample - startSample
		wf.setpos(startSample)
		samps = list(array.array("i", wf.readframes(samplesToRead)))

	except Exception as error:
		print(f"[E] error while reading samples: {error}")

	return [samps, fs]

def peak_detect(data):
	max_val = numpy.amax(abs(data))
	peak_ndx = numpy.where(data == max_val)

	if len(peak_ndx[0]) == 0:
		peak_ndx = numpy.where(data == -max_val)

	return peak_ndx

def calculateBpm(data, fs):
	cA = []
	cD = []
	correl = []
	cD_sum = []
	levels = 4
	max_decimation = 2 ** (levels - 1)
	min_ndx = math.floor(60.0 / 220 * (fs / max_decimation))
	max_ndx = math.floor(60.0 / 40 * (fs / max_decimation))

	for loop in range(0, levels):
		cD = []

		if loop == 0:
			[cA, cD] = pywt.dwt(data, "db4")
			cD_minlen = len(cD) / max_decimation + 1
			cD_sum = numpy.zeros(math.floor(cD_minlen))
		else:
			[cA, cD] = pywt.dwt(cA, "db4")

		cD = signal.lfilter([0.01], [1 - 0.99], cD)
		cD = abs(cD[:: (2 ** (levels - loop - 1))])
		cD = cD - numpy.mean(cD)
		cD_sum = cD[0 : math.floor(cD_minlen)] + cD_sum

	if [b for b in cA if b != 0.0] == []:
		print("[i] No audio data!")
		return None

	cA = signal.lfilter([0.01], [1 - 0.99], cA)
	cA = abs(cA)
	cA = cA - numpy.mean(cA)
	cD_sum = cA[0 : math.floor(cD_minlen)] + cD_sum
	correl = numpy.correlate(cD_sum, cD_sum, "full")
	midpoint = math.floor(len(correl) / 2)
	correl_midpoint_tmp = correl[midpoint:]
	peak_ndx = peak_detect(correl_midpoint_tmp[min_ndx:max_ndx])

	if len(peak_ndx) > 1:
		print("[i] No audio data!")
		return None

	peak_ndx_adjusted = peak_ndx[0] + min_ndx
	bpm = 60.0 / peak_ndx_adjusted * (fs / max_decimation)
	return [bpm, correl]

def getBpm(samps, fs, windowSize):
	data = []
	correl = []
	bpm = 0
	n = 0
	nsamps = len(samps)
	window_samps = int(windowSize * fs)
	samps_ndx = 0
	max_window_ndx = math.floor(nsamps / window_samps)
	bpms = numpy.zeros(max_window_ndx)

	for window_ndx in range(0, max_window_ndx):
		data = samps[samps_ndx : samps_ndx + window_samps]

		if not ((len(data) % window_samps) == 0):
			raise AssertionError(str(len(data)))

		calculatedData = calculateBpm(data, fs)
		if calculatedData == None:
			continue
		bpm = calculatedData[0]
		correl_temp = calculatedData[1]

		bpms[window_ndx] = bpm
		correl = correl_temp
		samps_ndx = samps_ndx + window_samps
		n = n + 1

	return numpy.median(bpms)




def plotBpm(filename, num_samples, sample_length, window_size, min_bpm, max_bpm):
	fileLength = int(float(subprocess.check_output("ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '" + filename + "'", shell=True).decode('utf-8').strip()))
	sampleRate = read_wav(filename, 0, 1)[1]

	bpmData = []
	timeData = []
	print(f"{filename}: {fileLength}s at {sampleRate}hz")

	for i in range(0, fileLength, int(fileLength / num_samples)):
		endTime = i + sample_length
		wavData = read_wav(filename, i, endTime)
		currentBpm = getBpm(wavData[0], sampleRate, window_size)
		if min_bpm < currentBpm < max_bpm:
			bpmData.append(currentBpm)
			timeData.append(formatSeconds(i))
			print(f"{i:5}s -> {endTime:5}s: {round(currentBpm, 5):6} bpm")
		else:
			print(f"{i:5}s -> {endTime:5}s: {round(currentBpm, 5):6} bpm <- SKIPPING")

	plt.plot(timeData, bpmData)
	plt.xlabel("Time")
	plt.ylabel("BPM")
	plt.ylim(min(bpmData) - 0.5, max(bpmData) + 0.5)
	plt.grid(axis='y')
	plt.xticks(rotation=45)
	plt.show()


def main():
	parser = argparse.ArgumentParser(description="Calculate and plot BPM from an audio file.")
	parser.add_argument("filename", help="input audio file")
	parser.add_argument("-s", "--samples", type=int, default=60, help="number of samples")
	parser.add_argument("-l", "--length", type=int, default=16, help="sample length in seconds")
	parser.add_argument("-w", "--window", type=float, default=3.0, help="window size in seconds")
	parser.add_argument("--min-bpm", type=int, default=120, help="minimum safe BPM range")
	parser.add_argument("--max-bpm", type=int, default=150, help="maximum safe BPM range")
	args = parser.parse_args()

	if not os.path.exists(args.filename):
		print("File not found.")
		return

	if not args.filename.lower().endswith((".wav", ".wave")):
		temp_dir = tempfile.gettempdir()
		converted_file = convertToWav(args.filename, temp_dir)
		plotBpm(converted_file, args.samples, args.length, args.window, args.min_bpm, args.max_bpm)
		shutil.rmtree(temp_dir, ignore_errors=True)
	else:
		plotBpm(args.filename, args.samples, args.length, args.window, args.min_bpm, args.max_bpm)

if __name__ == "__main__":
	main()