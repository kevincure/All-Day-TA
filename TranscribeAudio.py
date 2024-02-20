# Uses Whisper to transcribe audio files (mp3, mp4 or wav)

import os
import openai
from glob import glob
import re

def read_settings(file_name):
    settings = {}
    with open(file_name, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            settings[key] = value
    return settings
settings = read_settings("settings.txt")
savename = settings["filedirectory"]
professor = settings["professor"]
classname = settings["classname"]
with open("APIkey.txt", "r") as f:
    openai.api_key = f.read().strip()
    
model_id = "whisper-1"
folder_path = 'Chunked Audio'
os.makedirs('Transcriptions', exist_ok=True)

def transcribe_audio(model_id, audio_file_path):
    with open(audio_file_path, 'rb') as media_file:
        response = openai.Audio.transcribe(
            model=model_id,
            file=media_file,
            prompt=prompt_text
        )
    return response['text']

file_extensions = ["*.mp3", "*.mp4", "*.wav"]
files = []
for ext in file_extensions:
    files.extend(glob(os.path.join(folder_path, ext)))


for file in sorted(files, key=lambda x: int(re.search(r'part(\d+)', x).group(1))):
    file_name = os.path.basename(file)
    base_name, _ = os.path.splitext(file_name)
    lecture_name = re.sub(r'-part\d+', '', base_name)
    prompt_text = f'This is the transcription of a lecture from a {classname} taught by {professor}.'

    transcript = transcribe_audio(model_id, file)

    with open(f'transcriptions/{base_name}_transcript.txt', 'w', encoding='utf-8') as transcript_file:
        transcript_file.write(transcript)
        print(f"Writing {file}")

    with open(f'transcriptions/{lecture_name}_concatenated_transcript.txt', 'a', encoding='utf-8') as concatenated_file:
        concatenated_file.write(transcript)
        concatenated_file.write('\n\n')

    part_number = int(re.search(r'part(\d+)', base_name).group(1))
    if part_number > 1:
        with open(f'transcriptions/{lecture_name}_concatenated_transcript.txt', 'r', encoding='utf-8') as prev_concatenated_file:
            prev_text = prev_concatenated_file.read()
        words = prev_text.split()
        prompt_text = f'This is the transcription of a lecture from a {classname} taught by {professor}. The prior section of audio concludes {" ".join(words[-100:])}'
