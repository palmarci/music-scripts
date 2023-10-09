import argparse
import wave
import os
import shutil
import subprocess
import json
import tempfile
from datetime import datetime, timedelta

class Result:
	def __init__(self, title, segment_name):
		self.title = title
		self.timestamp = self.parse_timestamp(segment_name)

	@staticmethod
	def parse_timestamp(segment_name):
		segments = segment_name.split('_')
		hours = int(segments[0])
		minutes = int(segments[1])
		seconds = int(segments[2])
		return timedelta(hours=hours, minutes=minutes, seconds=seconds)

	def __str__(self):
		return f'{self.title} @ {self.timestamp}'

def check_and_convert_to_wav(input_file):
	# Check if the input file is already in WAV format
	if input_file.lower().endswith('.wav'):
		return input_file

	# Create a temporary directory to store the converted WAV file
	temp_dir = tempfile.mkdtemp(prefix='tmp_')

	# Generate the output WAV file path
	output_wav_file = os.path.join(temp_dir, 'converted.wav')

	# Use FFmpeg to convert the input file to WAV format
	print(f"Converting to {output_wav_file}...")
	command = f'ffmpeg -i "{input_file}" -hide_banner -loglevel panic "{output_wav_file}"'
	subprocess.run(command, shell=True)
	print("Converted to WAV")

	return output_wav_file

def get_segment_name(segment_index, segment_duration, skip_duration):
	start_time = segment_index * (segment_duration + skip_duration)
	hours = int(start_time / 3600)
	minutes = int((start_time % 3600) / 60)
	seconds = int(start_time % 60)
	return f'{hours:02d}_{minutes:02d}_{seconds:02d}'

def print_summary(results, occurrences, time_window):
	printed_titles = set()

	summary_lines = []
	for result_obj in results:
		title = result_obj.title
		if title not in printed_titles:
			count = sum(1 for res in results if res.title == title and abs(res.timestamp - result_obj.timestamp) <= time_window)
			if count >= occurrences:
				text_to_print = f'{result_obj.title} @ {result_obj.timestamp}'
				summary_lines.append(text_to_print)
				printed_titles.add(title)

	print("\n----------")
	print("\n".join(summary_lines))
	print("\nThis is an automatically generated tracklist. Please reply with your suggestions and corrections.")
	print("----------")

def process_wav_data(input_file, output_dir, segment_duration, skip_duration, occurrences, time_window):
	# Open the input WAV file
	with wave.open(input_file, 'rb') as wav_file:
		# Get the parameters of the input file
		num_channels = wav_file.getnchannels()
		sample_width = wav_file.getsampwidth()
		frame_rate = wav_file.getframerate()
		total_frames = wav_file.getnframes()

		# Calculate the number of frames for the segment and skip durations
		segment_frames = int(segment_duration * frame_rate)
		skip_frames = int(skip_duration * frame_rate)

		# Create the output directory if it doesn't exist
		os.makedirs(output_dir, exist_ok=True)

		# Split the WAV file into segments
		segment_count = 0
		start_frame = 0
		allResults = []

		while start_frame < total_frames:
			# Calculate the end frame for the current segment
			end_frame = start_frame + segment_frames

			# Set the position in the input file
			wav_file.setpos(start_frame)

			# Read frames for the current segment
			frames = wav_file.readframes(segment_frames)

			# Create a new output WAV file
			segment_name = get_segment_name(segment_count, segment_duration, skip_duration)
			output_file = os.path.join(output_dir, f'segment_{segment_name}.wav')
			with wave.open(output_file, 'wb') as output_wav:
				# Set the output file parameters
				output_wav.setnchannels(num_channels)
				output_wav.setsampwidth(sample_width)
				output_wav.setframerate(frame_rate)
				output_wav.writeframes(frames)

			# Run the songrec command for the segment
			segment_filename = f'segment_{segment_name}.wav'

			command = f'songrec audio-file-to-recognized-song "{output_file}"'
			result = subprocess.check_output(command, shell=True).decode().strip()

			# Process the songrec output
			result_data = json.loads(result)
			if "track" in result_data:
				title = result_data["track"]["subtitle"] + ' - ' + result_data["track"]["title"]
				result_obj = Result(title, segment_name)
				allResults.append(result_obj)
				print(result_obj)

			segment_count += 1
			start_frame += segment_frames + skip_frames

		print_summary(allResults, occurrences, time_window)

def main():
	# Create an argument parser
	parser = argparse.ArgumentParser(description='Detects the track IDs from a DJ mix using SongRec (Shazam). SongRec should be in PATH!')

	# Add the input file path argument
	parser.add_argument('input_file', type=str, help='path to the input file')

	# Add optional arguments for segment duration, skip duration, occurrences, time window, and output directory
	parser.add_argument('--segment-duration', type=float, default=15,
						help='duration of each segment in seconds (default: 15)')
	parser.add_argument('--skip-duration', type=float, default=15,
						help='duration to skip between segments in seconds (default: 15)')
	parser.add_argument('--occurrences', type=int, default=2,
						help='minimum number of occurrences for a result to be printed (default: 2)')
	parser.add_argument('--time-window', type=int, default=5,
						help='time window in minutes to consider for occurrences (default: 5)')

	# Parse the command-line arguments
	args = parser.parse_args()

	# Extract the input file path from the arguments
	input_file = args.input_file

	# Check if the input file exists
	if not os.path.isfile(input_file):
		print('The input file does not exist.')
		return

	# Convert the input file to WAV if necessary
	input_file = check_and_convert_to_wav(input_file)

	# Extract the segment duration, skip duration, occurrences, and time window from the arguments
	segment_duration = args.segment_duration
	skip_duration = args.skip_duration
	occurrences = args.occurrences
	time_window = timedelta(minutes=args.time_window)

	# Create a temporary directory to store the output segments
	with tempfile.TemporaryDirectory(prefix='output_') as output_dir:
		# Call the process_wav_data function
		process_wav_data(input_file, output_dir, segment_duration, skip_duration, occurrences, time_window)

if __name__ == '__main__':
	main()
