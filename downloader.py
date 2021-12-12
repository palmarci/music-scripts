import os
import youtube_dl


links = {
	"1212": "https://www.youtube.com/playlist?list=PLN_vS3zireLBr8fixcg4T8FdMotoNWRXE"
}

mainWorkingDir = os.getcwd()

def normalizeFilename(name):
	return name.replace(' - Topic', '').replace('.', '').replace("'", '').replace(':', '')

for currentName in links:
	os.chdir(mainWorkingDir)
	currentLink = links[currentName]
	print(f"{currentName}: [{currentLink}]")

	if os.path.exists(os.path.join(mainWorkingDir, currentName)) == False:
		print("folder '" + currentName + "' does not exist, creating...")
		os.mkdir(os.path.join(mainWorkingDir, currentName))

	os.chdir(os.path.join(mainWorkingDir, currentName))

	ydl = youtube_dl.YoutubeDL({'quiet': True})
	video = ""
	with ydl:
		result = ydl.extract_info(currentLink, download=False)
		if 'entries' in result:
			video = result['entries']
			for i, item in enumerate(video):

				# found video
				video = result['entries'][i]
				print(f"{i+1}/{len(result['entries'])}: {video['title']} [{video['id']}]")
				
				# get output name
				dlFileName = normalizeFilename(video["title"] + " - " + video["uploader"]) + "." + video["ext"]
				
				# download audio
				dlCommand = 'yt-dlp -f bestaudio -o "' + dlFileName + '" "https://www.youtube.com/watch?v=' + video["id"] + '"'
				os.system(dlCommand)
				
				# pass it to the converter/normalizer
				normalizeCommand = "python '" + mainWorkingDir + "/normalizer.py' '" + dlFileName + "'"
				os.system(normalizeCommand)

	os.chdir(mainWorkingDir)
