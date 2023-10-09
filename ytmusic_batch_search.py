import ytmusicapi
import subprocess
import argparse
import concurrent.futures
import os

yt = ytmusicapi.YTMusic(".oauth.json")
maxLegnth = 0
errorList = []

def log(msg):
	print(msg, flush=True)

def error(msg):
	global errorList
	errorList.append(msg)

def process_line(line):
	line = line.strip()
	try:
		results = yt.search(line, filter='songs', limit=1)
		if len(results) > 0 and "videoId" in results[0]:
			videoid = results[0]["videoId"]
			command = f'yt-dlp -J "https://music.youtube.com/watch?v={videoid}" | jq ".duration"'

			output = subprocess.check_output(command, shell=True)
			numbers = [int(i) for i in output.split() if i.isdigit()]
			length = int(''.join(str(v) for v in numbers))

			if length < maxLegnth * 60:
				log(videoid)
			else:
				error(f'exceeded time limit: {line}')
		else:
			error(f'not found: {line}')
	except Exception as e:
		error(f'{line}: {e}')



def main():
	global maxLegnth
	parser = argparse.ArgumentParser(description='Search every line in a given file on YT Music and print the best result\'s video ID.')
	parser.add_argument('file', type=str, help='Path to the file')
	parser.add_argument('--threads', type=int, default=os.cpu_count() - 1, help='Number of threads')
	parser.add_argument('--max-length', type=int, default=15, help='Max video length in minutes (Default: 15)')
	args = parser.parse_args()
	maxLegnth = args.max_length

	with open(args.file, 'r') as file:
		lines = file.readlines()

	log(f"running on {args.threads} threads")
	with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
		executor.map(process_line, lines)
	
	for i in errorList:
		log(i)


if __name__ == '__main__':
	main()
