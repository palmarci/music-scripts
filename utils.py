import logging
import shutil
import subprocess
import sys
import json
import hashlib
import os

def setup_logging(enable_debug:bool):
	target_level = logging.DEBUG if enable_debug else logging.INFO
	logging.basicConfig(
		level=target_level,
		format='%(asctime)s - %(levelname)s - %(message)s',
		handlers=[
			logging.StreamHandler(sys.stdout)
		]
	)
	return

def run_command(command) -> str:
	logging.debug(f"running command: {command}")
	result = subprocess.run(command, shell=True, capture_output=True, text=True)
	if result.returncode != 0:
		logging.error(f"command failed: {command}")
		logging.error(result.stderr)
		sys.exit(1)
	return_text = result.stdout + result.stderr
	return return_text # ffmpeg returns the analysis data in stderr somehow

def extract_ffmpeg_json(output:str):
	start_idx = output.find('{')
	end_idx = output.rfind('}') + 1
	json_str = output[start_idx:end_idx]
	data = json.loads(json_str)
	logging.debug(f"extracted json data: {data}")
	return data

def get_loudness_values(json_data, from_input=True):
	tag = "input" if from_input else "output"
	i = float(json_data[tag + "_i"])
	tp = float(json_data[tag + "_tp"])
	lra = float(json_data[tag + "_lra"])
	thresh = float(json_data[tag + "_thresh"])
	return i, tp, lra, thresh

def get_song_loudness_data(input_file_path:str):
	analyze_command = f"ffmpeg -i '{input_file_path}' -af loudnorm=print_format=json -f null -"
	out = run_command(analyze_command)
	analysis_data = extract_ffmpeg_json(out)
	return get_loudness_values(analysis_data, from_input=True)

def normalize_to_mp3(input_wav_path:str, output_mp3_path:str, target_tp:float=-0.1, target_lufs:float=-10.0) -> bool:
	# analyze the file with ffmpeg
	input_integrated, input_tp, input_lra, input_thresh = get_song_loudness_data(input_wav_path)

	# calculate the required gain
	required_gain = round(target_lufs - input_integrated, 2)
	if required_gain > 0:
		logging.warning("We are trying to make the song louder!")

	# determine if achieving the target loudness is possible without clipping
	forecasted_true_peak = round((input_tp + required_gain), 2)
	if forecasted_true_peak > target_tp:
		delta = (forecasted_true_peak - target_tp)
		target_lufs = round(target_lufs - (delta + 0.1), 2) # just to be on the safe side
		logging.warning(f"Target LUFS is not possible in linear mode. Lowered target by additional {delta} to {target_lufs}, to avoid clipping.")

	# normalize & convert to mp3
	normalize_command = (
		f"ffmpeg -i '{input_wav_path}' "
		f"-af loudnorm=I={target_lufs}:TP={target_tp}:LRA={input_lra}:linear=true:"
		f"measured_I={input_integrated}:measured_TP={input_tp}:"
		f"measured_LRA={input_lra}:measured_thresh={input_thresh}:print_format=json "
		f"-c:a libmp3lame -b:a 320k '{output_mp3_path}'"
	)
	out = run_command(normalize_command)

	# check if we got linear or not
	normalize_results = extract_ffmpeg_json(out)
	if normalize_results["normalization_type"] == "dynamic":
		logging.error("failed to run linear normalization")
		return False
	return True

def check_dependencies(dependencies:list[str]):
	for dependency in dependencies:
		if not shutil.which(dependency):
			logging.error(f"Missing from PATH: {dependency}")
			sys.exit(1)

def is_audio_format(filename):
	audio_extensions = ['flac', 'alac', 'wav', 'aif', 'mp3', 'aac', 'm4a', 'webm', 'opus', 'ogg']
	_, file_extension = os.path.splitext(filename)
	file_extension = file_extension.lower().replace(".", "")
	return file_extension.lower() in audio_extensions

def get_file_hash(filename):
	# Calculate the MD5 hash of a file's name
	return hashlib.md5(filename.encode('utf-8')).hexdigest()

def get_files_recursive(directory):
	file_list = []
	for root, directories, files in os.walk(directory):
		for file in files:
			file_list.append(os.path.join(root, file))
	return file_list

def get_thread_count(is_debug):
	if is_debug:
		return 1
	else:
		return min(os.cpu_count() - 1, 8) # clamp to max 8 and also leave 1 core free
