# Runs through all mp3, mp4, wav in "Raw Audio", chunks them, and saves the files as under 25MB in "Chunked Audio"
# Even 3 hour files should be fine; beyond that point, you will need to manually break them.
# Run this before you run "TranscribeAudio"
# You need ffmpeg installed for this to work
# To install ffmpeg, see the ReadMe

import os
import ffmpeg

input_folder = 'Raw Audio'
output_folder = 'Chunked Audio'

def compress_audio(input_folder, output_folder):
    # Define the extensions to look for
    extensions = ['.mp3', '.mp4', '.wav', '.ogg']

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file)
        print("Loading " + file)
        if os.path.isfile(file_path) and os.path.splitext(file)[1] in extensions:
            output_file = os.path.splitext(file)[0] + '.mp3'  # Change output extension to .mp3
            output_path = os.path.join(output_folder, output_file)

            # Compress the file using FFmpeg, switching to libmp3lame for MP3 encoding
            # Adjust bitrate as needed to balance quality and file size
            ffmpeg.input(file_path).output(output_path, vn=None, map_metadata="-1", ac=1,
                                           **{'c:a': 'libmp3lame', 'b:a': '32k'}).run(overwrite_output=True)
            print(f"Compressed and saved: {output_file}")


# Run the compression
compress_audio(input_folder, output_folder)
