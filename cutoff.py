from scipy.fft import fft, ifft
from pylab import *
import numpy as np
import scipy.io.wavfile as wav
import sys

def getAverageByHertzRange(dataSet, wantedHzBeginning, wantedHzEnd, samplesPerHz):
	data = dataSet[int(wantedHzBeginning * samplesPerHz):int(wantedHzEnd * samplesPerHz)]
	return sum(data) / len(data)

def get_song_data(samp_freq, snd):
	channel = snd[:, 0]
	time_array = arange(0, float(snd.shape[0]), 1)

	time_array = time_array / samp_freq
	time_array = time_array * 1000

	return time_array, channel

def getCutoff(filename, minSearchHz, maxSearchHz, hzStep):
	samp_freq, snd = wav.read(filename)
 
	if snd.dtype == dtype('int16'):
		snd = snd / (2. ** 15)
	else: 
		snd = snd / (2. ** 31)
	
	time_array, channel = get_song_data(samp_freq, snd)    
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

	averages = []
	samplesPerHz = 1/ (samp_freq / num_sample_points)
	
	for i in range(minSearchHz, maxSearchHz, hzStep):
		currentAvg = getAverageByHertzRange(10*log10(p), i - hzStep/2, i + hzStep/2, samplesPerHz)
		averages.append([i, currentAvg])
		#print(f"{i}hz: {currentAvg}")
	
	sumOfAverages = 0 
	for i in averages:
		sumOfAverages += i[1]

	avgOfAverages = sumOfAverages / len(averages)
	foundCutoff = False
	cutoff = 0

	i = 0
	while i < len(averages) and foundCutoff == False:
		if averages[i][1] < avgOfAverages:
			#print("cutoff found at " + str(averages[i][0]) + "hz")
			foundCutoff = True
			cutoff = averages[i][0]
		i += 1

	return cutoff

def main():
	if len(sys.argv) < 2:
		print("usage: python cutoff.py [filename]")
	else:
		print(getCutoff(sys.argv[1], 10000, 24000, 1000))

main()
