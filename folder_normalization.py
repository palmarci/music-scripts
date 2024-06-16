import os
import sys
import subprocess
import argparse
import concurrent.futures
from glob import glob

normalizeList = []
checked = 0

def getFfmpegStats(filePath):
	command = f'ffmpeg -nostats -i "{filePath}" -filter_complex ebur128 -f null -'
	completed_process = subprocess.run(command, shell=True, capture_output=True, text=True)
	stats = completed_process.stderr
	summaryIndex = stats.rfind('Summary:')
	summaryList = stats[summaryIndex:].split()
	ILufs = float(summaryList[summaryList.index('I:') + 1])
	IThresh = float(summaryList[summaryList.index('I:') + 4])
	LRA = float(summaryList[summaryList.index('LRA:') + 1])
	LRAThresh = float(summaryList[summaryList.index('LRA:') + 4])
	LRALow = float(summaryList[summaryList.index('low:') + 1])
	LRAHigh = float(summaryList[summaryList.index('high:') + 1])
	statsDict = {'I': ILufs, 'I Threshold': IThresh, 'LRA': LRA, 'LRA Threshold': LRAThresh, 'LRA Low': LRALow, 'LRA High': LRAHigh}
	return statsDict

def runNormalization(filename, target_db):
	output = filename + "_normalized.mp3"
	applyCommand = f'ffmpeg-normalize "{filename}" --keep-loudness-range-target  -nt ebu -t {target_db} -tp -0.1 -c:a libmp3lame -b:a 320k -o "{output}"'
	normalizeProcess = subprocess.run(applyCommand, shell=True, capture_output=True, text=True)

	if normalizeProcess.returncode == 0:
		if os.path.exists(output):
			os.remove(filename)
			os.rename(output, filename)
			print(f"Normalization process completed successfully for {filename}.")
		else:
			print(f"Normalization output file does not exist for {filename}.")
	else:
		print(f"Normalization process failed for {filename}.")
		print("Error message:", normalizeProcess.stderr)
		print("Output message:", normalizeProcess.stdout)

def checkFile(filename, args):
	global checked

	loudnessStats = getFfmpegStats(filename)
	db = float(loudnessStats['I'])

	checked += 1

	if args.target_db - (args.skip_db / 2) < db and args.target_db + (args.skip_db / 2) > db:
		print(f"   [{checked}] {filename} ok")
	else:
		print(f"   {filename} requires normalization: {db}")
		if not args.dry_run:
			runNormalization(filename, args.target_db)

def main():
	print("TODO: dont use this, this needs to be reworked, linear gaining may fail and compromise the audio quality")
	return
	parser = argparse.ArgumentParser(description='Audio file normalization')
	parser.add_argument('folder', help='Input folder path')
	parser.add_argument('--target-db', type=float, default=-9.5, help='Target loudness level in LUFS (default: -9.5)')
	parser.add_argument('--dry-run', default=False, type=bool, help='Disable the actual normalization, just analyze')
	parser.add_argument('--skip-db', type=float, default=0.5, help='Maximum tolerated dB difference (default: 0.5)')
	args = parser.parse_args()

	mp3_files = glob(os.path.join(args.folder, '**/*.mp3'), recursive=True)

#	for i in mp3_files:
#		checkFile(i, args)

	num_threads = 3
	with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
		futures = [executor.submit(checkFile, filename, args) for filename in mp3_files]
		concurrent.futures.wait(futures)

if __name__ == '__main__':
	main()
