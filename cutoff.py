from scipy.fft import fft, ifft
from pylab import *
import numpy as np
import scipy.io.wavfile as wav
import sys
import matplotlib.pyplot as plt
import glob
import os
import subprocess

debugMode = False

def runCommand(command):
	subProcess = subprocess.check_output(command, shell=True)
	return str(subProcess.decode('utf-8'))

def getAverageByHertzRange(dataSet, wantedHzBeginning, wantedHzEnd, samplesPerHz):
	data = dataSet[int(wantedHzBeginning * samplesPerHz):int(wantedHzEnd * samplesPerHz)]
	return sum(data) / len(data)

def getSongData(samp_freq, snd):
	channel = snd[:, 0]
	time_array = arange(0, float(snd.shape[0]), 1)

	time_array = time_array / samp_freq
	time_array = time_array * 1000

	return time_array, channel

def getCutoff(filename, minSearchHz, maxSearchHz, hzStep, hzRange):
	samp_freq, snd = wav.read(filename)
 
	if snd.dtype == dtype('int16'):
		snd = snd / (2. ** 15)
	else: 
		snd = snd / (2. ** 31)
	
	time_array, channel = getSongData(samp_freq, snd)    
	num_sample_points = len(channel)

	p = fft(channel)

	nUniquePts = ceil((num_sample_points+1)/2.0)
	p = p[0:int(nUniquePts)]


	p = abs(p)
	p = p / float(num_sample_points)
	p = p**2

	if num_sample_points % 2 > 0: 
		p[1:len(p)] = p[1:len(p)] * 2
	else:
		p[1:len(p) - 1] = p[1:len(p) - 1] * 2 

	freq_array = arange(0, nUniquePts, 1.0) * (samp_freq / num_sample_points)

	#print("freqarray is done")
	#print(samp_freq / num_sample_points)

	#averages = []
	plotHzs = []
	plotDbs = []
	dbDifferences =  []

	samplesPerHz = 1/ (samp_freq / num_sample_points)
	
	for i in range(minSearchHz, maxSearchHz, hzStep):
		currentAvg = getAverageByHertzRange(10*log10(p), i - hzStep/2, i + hzStep/2, samplesPerHz)
		plotHzs.append([i])
		plotDbs.append(currentAvg)
		if debugMode:
			print(f"{i}hz: {currentAvg}")


	top = max(plotDbs)
	bot = min(plotDbs)
	avgs = []
	lowEnd = []

	for i in plotDbs:
		avgs.append(((i / top) * 100) - 100)

	worst = max(avgs)

	i = 0
	while i < len(avgs):
		if avgs[i] - hzRange / 2 < worst and worst < avgs[i] + hzRange / 2:
			lowEnd.append(i)
		i = i + 1 

	cutoff = plotHzs[(lowEnd[0] - 1)][0]

	if cutoff > 20000:
		cutoff = 20000

	if debugMode:
		print(avgs)
		print(lowEnd)
		plt.plot(plotHzs, plotDbs)
		plt.ylabel('db')
		plt.xlabel('Hz')
		plt.show()

	return cutoff

def main():
	if len(sys.argv) < 2:
		print("this script tries to detect the cutoff frequency of every file in a given folder\nusage: python cutoff.py [folder]")
	else:
		for file in glob.iglob(sys.argv[1]+ '*', recursive=True):
			filesplit = os.path.splitext(file)
			if filesplit[1] != "wav":
				runCommand("ffmpeg -y -nostats -loglevel panic -hide_banner -i '" + file + "' tmp.wav")

			cutoff = getCutoff("tmp.wav", 10000, 24000, 500, 12)

			if cutoff == 20000:
				print(f"{filesplit[0]}: ok")
			else:
				print(f"[!!!] {filesplit[0]}: {cutoff}")

			runCommand("rm tmp.wav")

main()
