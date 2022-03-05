from ShazamAPI import Shazam
from io import BytesIO 
import struct
import wave
import sys
import os
import subprocess

def runCommand(command):
	subProcess = subprocess.getoutput(command)
	return str(subProcess)

# config
timeBetweeenSamples = 60
sampleLength = 15
minOccurance = 2


# variables
wavFrameRate = 0
wavSampWidth = 0
wavChannels = 0
matches = []

def signalToWavFormat(signal):
	memoryFile = BytesIO(b"")
	wavFile = wave.open(memoryFile, 'wb')
	wavFile.setnchannels(wavChannels)
	wavFile.setsampwidth(wavSampWidth)
	wavFile.setframerate(wavFrameRate)
	wavFile.writeframes(signal)
	wavFile.close()
	memoryFile.seek(0)
	return memoryFile.read()

if len(sys.argv) > 1:
	if os.path.exists(sys.argv[1]):

		# convert to wav
		print("converting to wav...")
		originalFilename = os.path.abspath(sys.argv[1])
		workingFilePath = f'/tmp/{os.path.splitext(os.path.basename(originalFilename))[0]}.wav'
		ffmpegCommand = f'ffmpeg -loglevel quiet -n -i "{originalFilename}" "{workingFilePath}"'
		runCommand(ffmpegCommand)

		# read fileSeconds
		getfileSecondsCommand = "ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '" + workingFilePath + "'"
		resp = runCommand(getfileSecondsCommand)
		fileSeconds = round(float(resp))
		print(f"loaded '{os.path.basename(workingFilePath)}' -> {fileSeconds} s")
		
		# read chunks from wav
		with wave.open(workingFilePath, "rb") as infile:
			wavChannels = infile.getnchannels()
			wavSampWidth = infile.getsampwidth()
			wavFrameRate = infile.getframerate()

			# loop on the chunks
			for i in range(0, fileSeconds):
				if i % (timeBetweeenSamples + sampleLength) == 0:

					infile.setpos(int(i * wavFrameRate))
					data = infile.readframes(int(((i + sampleLength) - i) * wavFrameRate))

					# run shazam
					shazam = Shazam(signalToWavFormat(data))
					recognizer = shazam.recognizeSong()
					response = list(recognizer)

					# get matches
					track = ""
					for r in response:
						if "track" in r[1]:
							artist = r[1]["track"]["subtitle"]
							title = r[1]["track"]["title"]
							track = f"{artist} - {title}"
							matches.append(track)

					print(f"{i} -> {i + sampleLength} (/{fileSeconds}): {track}")
		
		# filter false positives
		toOutput = []
		for i in matches:
			counter = 0
			for x in matches:
				if x == i:
					counter += 1
			if counter > minOccurance:
				toOutput.append(i)

		print("Shazam found these tracks:")
		for i in list(set(toOutput)):
			print(i)
	
	else:
		print("file not found")
else:
	print("usage: python mixDetect.py [filename]")
