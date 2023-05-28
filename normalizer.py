#!/usr/bin/python
import os
import sys
import re
import subprocess

targetDb = -9.5 #lufs
cuttoffHz = 20000
codecBitrate = 256

def runCommand(command):
	subProcess = subprocess.check_output(command, shell=True)
	return str(subProcess.decode('utf-8'))

def r128Stats(filePath):
	ffargs = ['ffmpeg', '-nostats', '-i', filePath, '-filter_complex', 'ebur128', '-f', 'null', '-']
	try:
		#print(ffargs)
		proc = subprocess.Popen(ffargs, stderr=subprocess.PIPE)
		stats = proc.communicate()[1]
		stats = stats.decode('utf-8')
		#print(stats)
		summaryIndex = stats.rfind('Summary:')
		summaryList = stats[summaryIndex:].split()
		ILufs = float(summaryList[summaryList.index('I:') + 1])
		IThresh = float(summaryList[summaryList.index('I:') + 4])
		LRA = float(summaryList[summaryList.index('LRA:') + 1])
		LRAThresh = float(summaryList[summaryList.index('LRA:') + 4])
		LRALow = float(summaryList[summaryList.index('low:') + 1])
		LRAHigh = float(summaryList[summaryList.index('high:') + 1])
		statsDict = {'I': ILufs, 'I Threshold': IThresh, 'LRA': LRA, 'LRA Threshold': LRAThresh, 'LRA Low': LRALow, 'LRA High': LRAHigh}

	except Exception as e:
		print(f"[E] Error while getting loudness data: {e}")
		sys.exit(1)

	return statsDict


def linearGain(iLUFS, goalDB):
	gainLog = -(iLUFS - goalDB)
	return 10 ** (gainLog / 20)


def applyGain(inPath, outPath, linearAmount):
	applyCommand = 'ffmpeg -i "' + inPath + '" -nostats -loglevel 0 -af volume=' + str(linearAmount) +' -f caf - | fdkaac -w ' + str(cuttoffHz) + ' -b ' + str(codecBitrate) + ' - -o "' + outPath + '"' 

	try:
		runCommand(applyCommand)

	except Exception as e:
		print(f"[E] Error while applying gain: {e}")
		return False

	return True

def startNormalization(filePath):
	loudnessStats = r128Stats(filePath)

	if not loudnessStats:
		print("[E] Got empty loudness data!")
		sys.exit(1)

	gainAmount = linearGain(loudnessStats['I'], targetDb)
	outputPath = os.path.splitext(filePath)[0]  + ".m4a"

	if os.path.isfile(outputPath):
		print("[I] Skipping file, already exists at " + outputPath)
	else:
		gainSuccess = applyGain(filePath, outputPath, gainAmount)
		if not gainSuccess:
			sys.exit(1)


def main():
	fileName = str(sys.argv[1])
	#filePathWav = os.path.splitext(fileName)[0] + ".wav"
	#runCommand('ffmpeg -i "' + fileName + '" -y -nostats -loglevel 0 "' + filePathWav + '"')

	startNormalization(fileName)

	#runCommand("rm '" + filePathWav + "'")
	runCommand('rm "' + fileName + '"')

main()
