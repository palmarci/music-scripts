import os
import subprocess
import datetime
import argparse
import shutil

def convert_to_mp3(input_file, output_file):
	# Convert WAV to MP3 using ffmpeg
	subprocess.call(['ffmpeg', '-i', input_file, '-b:a', '320k', output_file])

def convert_folder_to_mp3(input_folder, output_folder, output_format):
	
	if os.path.isdir(output_folder):
		raise Exception("Output folder already exists!")
		#shutil.rmtree(output_folder)
	
	os.mkdir(output_folder)
	
	for root, dirs, files in os.walk(input_folder):
		for file in files:
			if file.endswith('.wav'):
				wav_file = os.path.join(root, file)
				
				# Get last modification date and time
				modified_time = os.path.getmtime(wav_file)
				modified_datetime = datetime.datetime.fromtimestamp(modified_time)
				
				# Generate output filename
				output_filename = modified_datetime.strftime(output_format)
				output_file = os.path.join(output_folder, output_filename + '.mp3')
				#output_file = f'{output_folder}{output_filename}.mp3'

				# Convert WAV to MP3
				convert_to_mp3(wav_file, output_file)
				
				print(f"Converted '{wav_file}' to '{output_file}'")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Convert WAV files in a folder to MP3.')
parser.add_argument('input_folder', type=str, help='Input folder path containing the WAV files')
parser.add_argument('output_folder', type=str, help='Output folder path containing the MP3 files')
parser.add_argument('--output-text-format', type=str, default="%Y_%m_%d__%H_%M", help='Output filename date format (default: %(default)s)')
args = parser.parse_args()

# Convert folder to MP3
convert_folder_to_mp3(args.input_folder, args.output_folder, args.output_text_format)
