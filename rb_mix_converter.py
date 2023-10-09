import os
import subprocess
import datetime
import argparse
import shutil

output_folder = '/tmp/converted/'

def convert_to_mp3(input_file, output_file):
	# Convert WAV to MP3 using ffmpeg
	subprocess.call(['ffmpeg', '-i', input_file, '-b:a', '320k', output_file])

def convert_folder_to_mp3(folder_path, output_format):
	
	if os.path.isdir(output_folder):
		shutil.rmtree(output_folder)
	
	os.mkdir(output_folder)
	
	for root, dirs, files in os.walk(folder_path):
		for file in files:
			if file.endswith('.wav'):
				wav_file = os.path.join(root, file)
				
				# Get last modification date and time
				modified_time = os.path.getmtime(wav_file)
				modified_datetime = datetime.datetime.fromtimestamp(modified_time)
				
				# Generate output filename
				output_filename = modified_datetime.strftime(output_format)
				#output_file = os.path.join(root, output_filename + '.mp3')
				output_file = f'{output_folder}{output_filename}.mp3'

				# Convert WAV to MP3
				convert_to_mp3(wav_file, output_file)
				
				print(f"Converted '{wav_file}' to '{output_file}'")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Convert WAV files in a folder to MP3.')
parser.add_argument('folder', type=str, help='Folder path containing WAV files')
parser.add_argument('--output-format', type=str, default="%Y_%m_%d__%H_%M", help='Output filename format (default: %(default)s)')
args = parser.parse_args()

# Convert folder to MP3
convert_folder_to_mp3(args.folder, args.output_format)
