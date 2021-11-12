#!/usr/bin/python
import os
import sys
import re
import subprocess

expectedDb = -11 # LUFS or db ????
cuttoffHz = 20000
codecBitrate = 256

def runCommand(command):
	subProcess = subprocess.check_output(command, shell=True)
	return str(subProcess.decode('utf-8'))

def r128Stats(filePath):
	ffargs = ['ffmpeg', '-nostats', '-i', filePath, '-filter_complex', 'ebur128', '-f', 'null', '-']
	try:
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

def startNormalization(filePath, quality):
	loudnessStats = r128Stats(filePath)

	if not loudnessStats:
		print("[E] Got empty loudness data!")
		sys.exit(1)

	gainAmount = linearGain(loudnessStats['I'], expectedDb)
	outputPath = os.path.splitext(filePath)[0]  + quality + ".m4a"
	#filePath = os.path.splitext(fileName)[0] + ".wav"

	if os.path.isfile(outputPath):
		print("[I] Skipping file, already exists at " + outputPath)
	else:
		gainSuccess = applyGain(filePath, outputPath, gainAmount)
		if not gainSuccess:
			sys.exit(1)


def getQuality(fileName):
	soxiResult = runCommand('soxi "' + fileName + '"')
	regexValue = re.findall(r'(?!Bit Rate *: )([1-9]\.[1-9][1-9])', soxiResult)

	if len(regexValue) > 0:
		bitRate = float(regexValue[0])
		return bitRate
	else:
		print("[E] Could not get the wav bit rate!")
		sys.exit(1)

def main():
	fileName = str(sys.argv[1])
	filePathWav = os.path.splitext(fileName)[0] + ".wav"
	runCommand('ffmpeg -i "' + fileName + '" -y -nostats -loglevel 0 "' + filePathWav + '"')

	qualityString = "Q" + str((abs(getQuality(filePathWav)))).replace(".", "-")
	print(f"{filePathWav}: {qualityString}")

	#startNormalization(fileName, qualityString)
	startNormalization(fileName, "")

	runCommand("rm '" + filePathWav + "'")
	runCommand('rm "' + fileName + '"')

main()
