import os
from yt_dlp import YoutubeDL
import time
import multiprocessing

links = {
	"EDITME": "https://www.youtube.com/playlist?list=EDITME",
}

mainWorkingDir = os.getcwd()

def normalizeFilename(name):
	name = name.strip()
	name = name.replace(' - Topic', '').replace('.', '').replace("'", '').replace(':', '').replace("/", "").replace('"', '')
	return name

def downloadVideo(video):
	if video is None or video['title'] is None or video["id"] is None:
		return

	print(f"{video['title']} - [{video['id']}]")
				
	dlFileName = normalizeFilename(video["title"] + " - " + video["uploader"]) + ".wav"
				
	dlCommand = f'yt-dlp -q -f bestaudio -o "{dlFileName}" --extract-audio --audio-format wav "https://www.youtube.com/watch?v={video["id"]}"'
	os.system(dlCommand)
				
	normalizeCommand = "python '" + mainWorkingDir + "/normalizer.py' '" + dlFileName + "'"
	os.system(normalizeCommand)


for currentName in links:
	os.chdir(mainWorkingDir)
	currentLink = links[currentName]
	print(f"{currentName}: [{currentLink}]")

	if os.path.exists(os.path.join(mainWorkingDir, currentName)) == False:
		print("folder '" + currentName + "' does not exist, creating...")
		os.mkdir(os.path.join(mainWorkingDir, currentName))

	os.chdir(os.path.join(mainWorkingDir, currentName))

	ydl = YoutubeDL({'quiet': False, 'verbose': False, 'ignoreerrors': True})

	videoList = []

	with ydl:
		try:
			time.sleep(0.1) # youtube api restriction by IP???
			result = ydl.extract_info(currentLink, download=False)
		except:
			print("failed video #{currentLink}")
			continue

		if 'entries' in result:
			videos = result['entries']
			for video in videos:
				videoList.append(video)
			fullSize = len(result['entries'])
			print(f"got {len(videoList)} / {fullSize} videos")

	cpu = os.cpu_count()
	if cpu >= 8:
		cpu = cpu -2
	else:
		cpu = cpu -1 

	print(f"starting with {cpu} threads")
	pool = multiprocessing.Pool(processes=cpu)
	pool.map(downloadVideo, videoList)

	os.chdir(mainWorkingDir)
