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
import subprocess

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
		print(f"[E] error while reading samples: {e}")

	# sample array, sample rate, length in seconds
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

		#bpm, correl_temp = calculateBpm(data, fs)
		calculatedData = calculateBpm(data, fs)
		if calculatedData == None:
			continue
		#if bpm is None:
		#	continue
		bpm = calculatedData[0]
		correl_temp = calculatedData[1]

		bpms[window_ndx] = bpm
		correl = correl_temp
		samps_ndx = samps_ndx + window_samps
		n = n + 1

	return numpy.median(bpms)

def convertToWav(filename):
	print("converting to wav...")
	originalFilename = os.path.abspath(filename)
	workingFilePath = f'/tmp/{os.path.splitext(os.path.basename(originalFilename))[0]}.wav'
	ffmpegCommand = f'ffmpeg -loglevel quiet -n -i "{originalFilename}" "{workingFilePath}"'
	subprocess.call(ffmpegCommand, shell=True)
	return workingFilePath

# how many samples, sample length in seconds, window size(?), safe bpm range
def plotBpm(filename, settings):

	fileLength = int(float(subprocess.check_output("ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '" + filename + "'", shell=True).decode('utf-8').strip()))
	sampleRate = read_wav(filename, 0, 1)[1]

	bpmData = []
	timeData = []
	print(f"{filename}: {fileLength}s at {sampleRate}hz")

	for i in range(0, fileLength, int(fileLength / settings[0])):
		endTime = i + settings[1]
		wavData = read_wav(filename, i, endTime)
		currentBpm = getBpm(wavData[0], sampleRate, settings[2])
		if settings[3][0] < currentBpm < settings[3][1]: 
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

if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
	filePath = sys.argv[1]
	if ".wav" not in sys.argv[1]:
		filePath = convertToWav(sys.argv[1])
		#print(filePath)
	plotBpm(filePath, [60, 16, 3.0, [120, 150]])

else:
	print("usage: python plotBpm.py [filename]")
