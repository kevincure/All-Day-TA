# This code takes all pdfs in documents, scans them, then generates paragraph embeddings on a sliding scale of 200 tokens (roughly 150 words)
# Run this before you run EmbedDocuments.py or app.py
# You need an OpenAI key saved in APIkey.txt
# Note that if your PDFs are not searchable, this won't work - use a third party tool to convert them to txt or doc first.  You
#   can look at the "-originaltext.csv" file created here and scan real quick to see if the text looks corrupted for any of your docs


import os
import time
import chardet
from PyPDF2 import PdfReader 
import nltk
import pandas as pd
import numpy as np
import json
import io
# you need to pip install python-docx, not docx
import docx
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


# Set the desired chunk size and overlap size
# chunk_size is how many tokens we will take in each block of text
# overlap_size is how much overlap. So 200, 100 gives you chunks of between the 1st and 200th word, the 100th and 300th, the 200 and 400th...
# I have in no way optimized these
chunk_size = 200
overlap_size = 100

# load user settings and api key
def read_settings(file_name):
    settings = {}
    with open(file_name, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            settings[key] = value
    return settings
settings = read_settings("settings.txt")
filedirectory = settings["filedirectory"]
# Check if the subfolder exists, if not, create it
output_folder = "Textchunks"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)


# Loop through all pdf, txt, tex in the "documents" folder
for filename in os.listdir(filedirectory):
    # Create an empty DataFrame to store the text and title of each document
    df = pd.DataFrame(columns=["Title", "Text"])
    print("Loading " + filename)
    if filename.endswith(".pdf"):
        # Open the PDF file in read-binary mode
        filepath = os.path.join(filedirectory, filename)
        reader = PdfReader(filepath)

        # Extract the text from each page of the PDF
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        # Add the text and title to the DataFrame
        title = os.path.splitext(filename)[0]  # Remove the file extension from the filename
        new_row = pd.DataFrame({"Title": [title], "Text": [text]})
        df = pd.concat([df, new_row], ignore_index=True)

    elif filename.endswith(".doc") or filename.endswith(".docx"):
        # Open the DOC/DOCX file in binary mode and read the raw data
        filepath = os.path.join(filedirectory, filename)
        doc = docx.Document(filepath)

        # Convert the file to UTF-8 and extract the text
        text = ''
        for paragraph in doc.paragraphs:
            text += paragraph.text

        # Add the text and title to the DataFrame
        title = os.path.splitext(filename)[0]  # Remove the file extension from the filename
        new_row = pd.DataFrame({"Title": [title], "Text": [text]})
        df = pd.concat([df, new_row], ignore_index=True)

    elif filename.endswith(".txt"):
        # Open the text file and read its contents
        filepath = os.path.join(filedirectory, filename)
        with open(filepath, "r", encoding="utf-8") as file:
            text = file.read()

        # Add the text and title to the DataFrame
        title = os.path.splitext(filename)[0]  # Remove the file extension from the filename
        new_row = pd.DataFrame({"Title": [title], "Text": [text]})
        df = pd.concat([df, new_row], ignore_index=True)
        
    elif filename.endswith(".tex"):
        # Use regular expressions to extract regular text from the LaTeX file
        filepath = os.path.join(filedirectory, filename)
        with open(filepath, "r", encoding="utf-8") as file:
            text = file.read()
        
        # Add the text and title to the DataFrame
        title = os.path.splitext(filename)[0] # Remove the file extension from the filename
        new_row = pd.DataFrame({"Title": [title], "Text": [text]})
        df = pd.concat([df, new_row], ignore_index=True)

    # Loop through the rows and create overlapping chunks for each text
    chunks = []
    for i, row in df.iterrows():
        # Tokenize the text for the current row
        tokens = nltk.word_tokenize(row['Text'])

        # Loop through the tokens and create overlapping chunks
        for j in range(0, len(tokens), chunk_size - overlap_size):
            # Get the start and end indices of the current chunk
            start = j
            end = j + chunk_size

            # Create the current chunk by joining the tokens within the start and end indices
            chunk = ' '.join(tokens[start:end])

            # Add the article title to the beginning of the chunk
            chunk_with_title = "This text comes from the document " + row['Title'] + ". " + chunk

            # Append the current chunk to the list of chunks, along with the corresponding title
            chunks.append([row['Title'], chunk_with_title])

    # Convert the list of chunks to a dataframe
    df_chunks = pd.DataFrame(chunks, columns=['Title', 'Text'])

    # Truncate the filename if it's too long, e.g., limit to 250 characters
    max_filename_length = 250
    if len(filename) > max_filename_length:
        filename = filename[:max_filename_length]

    # Remove the file extension from the filename
    filename_without_extension = os.path.splitext(filename)[0]

    # Save the df_chunks to the output_folder subfolder with the new file name
    output_file = os.path.join(output_folder, filename_without_extension + "-originaltext.csv")
    df_chunks.to_csv(output_file, encoding='utf-8', escapechar='\\', index=False)

    print("Saving " + filename)





