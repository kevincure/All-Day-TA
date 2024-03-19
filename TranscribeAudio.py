# Uses Whisper to transcribe audio files - the files will be in .mp3 format
# Run PrepareAudio.py first

import os
import openai
import subprocess
from glob import glob

def read_settings(file_name):
    settings = {}
    with open(file_name, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            settings[key] = value
    return settings


# Load settings and API key
settings = read_settings("settings.txt")
professor = settings["professor"]
classname = settings["classname"]
with open("APIkey.txt", "r") as f:
    openai.api_key = f.read().strip()

# Whisper model id
model_id = "whisper-1"
folder_path = 'Chunked Audio'  
os.makedirs('Transcriptions', exist_ok=True)

# if files are > than about an hour, chunk them to stay under Whisper 25MB limit
def split_file(file_path, chunk_size_mb=22, output_format='mp3'):
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb <= chunk_size_mb:
        # If file is already smaller than the target chunk size, no need to split
        print(f"No need to split {file_path} as it's under {chunk_size_mb}MB.")
        return [file_path]

    # Use ffprobe to calculate the total duration of the audio file in seconds
    total_duration_sec = float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration', '-of',
        'default=noprint_wrappers=1:nokey=1', file_path
    ], text=True).strip())
    print(f"Duration: {total_duration_sec} seconds")

    # Calculate the number of chunks needed
    file_duration_minutes = total_duration_sec / 60
    filesize_per_minute = file_size_mb / file_duration_minutes
    chunk_duration_minutes = chunk_size_mb / filesize_per_minute

    chunk_paths = []
    for i in range(0, int(total_duration_sec), int(chunk_duration_minutes * 60)):
        chunk_name = f"{os.path.splitext(file_path)[0]} - Part {len(chunk_paths) + 1}.{output_format}"
        # Use ffmpeg to split the file without re-encoding
        subprocess.run([
            'ffmpeg', '-i', file_path, '-ss', str(i), '-t', str(chunk_duration_minutes * 60),
            '-acodec', 'copy', chunk_name, '-y'
        ])
        chunk_paths.append(chunk_name)

    if chunk_paths:
        # If chunks were created, delete the original file
        os.remove(file_path)
        print(f"Deleted original file: {file_path}")

    return chunk_paths

# Transcribe with Whisper
def transcribe_audio(model_id, audio_file_path):
    with open(audio_file_path, 'rb') as media_file:
        response = openai.Audio.transcribe(model=model_id, file=media_file)
    return response['text']

# Modify the file processing to include chunking
files = glob(os.path.join(folder_path, "*.mp3"))

for file in files:
    # Chunk file if needed and obtain a list of file paths (chunked or original)
    print("Begin splitting " + file + " if necessary")
    chunked_files = split_file(file)
    # whisper can only take 25MB, which is roughly 3 hours of .ogg
    for chunk_file in chunked_files:
        # Check file size and skip if larger than 25MB
        if os.path.getsize(chunk_file) > 24 * 1024 * 1024:
            print(f"Skipping {chunk_file} due to size greater than 25MB.")
            continue

        print("Transcribing " + chunk_file)
        transcript = transcribe_audio(model_id, chunk_file)

        # Determine base name for saving the transcript
        base_name = os.path.splitext(os.path.basename(chunk_file))[0]
        transcript_path = os.path.join('Transcriptions', f'{base_name} Transcript.txt')

        with open(transcript_path, 'w', encoding='utf-8') as transcript_file:
            transcript_file.write(transcript)
            print(f"Transcript written for {chunk_file}")