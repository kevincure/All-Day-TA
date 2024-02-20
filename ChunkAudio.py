# Runs through all mp3, mp4, wav in "Raw Audio", chunks them, and saves the files as under 25MB in "Chunked Audio"
# Run this before you run "EmbedAudio"
# You need ffmpeg installed for this to work
# To install ffmpeg, you can follow the instructions given in the official documentation: https://ffmpeg.org/download.html

import os
from pydub import AudioSegment
from math import ceil

input_folder = 'Raw Audio'
output_folder = 'Chunked Audio'

def chunk_audio_file(input_file, output_folder, chunk_duration_minutes=5):
    # Supported formats
    formats = {
        '.mp3': 'mp3',
        '.mp4': 'mp4',
        '.m4a': 'm4a',
        '.wav': 'wav'
    }

    # Check if file format is supported
    file_format = os.path.splitext(input_file)[1]
    if file_format not in formats:
        print(f"Unsupported file format for file: {input_file}")
        return

    # Load the audio file
    audio = AudioSegment.from_file(input_file, format=formats[file_format])

    # Set the chunk duration in milliseconds
    chunk_duration_ms = chunk_duration_minutes * 60 * 1000

    # Get the original filename without extension
    filename_no_ext = os.path.splitext(os.path.basename(input_file))[0]

    # Split and export the chunks
    start_time = 0
    end_time = chunk_duration_ms
    part_counter = 1

    while start_time < len(audio):
        # Slice the audio
        chunk = audio[start_time:end_time]

        # Save the chunk
        chunk_filename = os.path.join(output_folder, f"{filename_no_ext}-part{part_counter}{file_format}")
        chunk.export(chunk_filename, format=formats[file_format])
        print(f"Saved chunk: {chunk_filename}")

        # Update counters and times
        start_time += chunk_duration_ms
        end_time += chunk_duration_ms
        part_counter += 1

def process_audio_files(input_folder, output_folder):
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Iterate over all files in the input folder
    for file in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file)
        
        # Check if it's a file (and not a folder)
        if os.path.isfile(file_path):
            chunk_audio_file(file_path, output_folder)

process_audio_files(input_folder, output_folder)