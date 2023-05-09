# This code embeds all the text chunks from ChopDocuments.py
# Run this before you run app.py
# Look at "-originaltext.csv" before you run this to make sure you docs scanned right!
# You need an OpenAI key saved in APIkey.txt
# Note there is a limit to how many things you can embed with the OpenAI API, so I split the documents to stay under
# This will only add new documents; every time you add something new, Chop it with ChopDocuments, then run this


import os
import time
import nltk
import pandas as pd
import numpy as np
import json
import openai
import io

embeddingmodel = "text-embedding-ada-002"
# Define the maximum number of tokens per batch to send to OpenAI for embedding per minute
MAX_TOKENS_PER_BATCH = 250000

output_folder = "Embedded Text"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# load user settings and api key
def read_settings(file_name):
    settings = {}
    with open(file_name, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            settings[key] = value
    return settings
settings = read_settings("settings.txt")
with open("APIkey.txt") as f:
    openai.api_key = f.read().strip()
    
# Define the function to send a batch of input text to the OpenAI API and return the embeddings
def embed_input_text(input_text_batch):
    embeddings = openai.Embedding.create(
        model=embeddingmodel,
        input=input_text_batch
    )
    return embeddings["data"]

# Load text data from Textchunks
folder = "Textchunks"
for file in os.listdir(folder):
    if file.endswith(".csv"):
        file_path = os.path.join(folder, file)
        df_chunks = pd.read_csv(file_path, encoding='utf-8', escapechar='\\')
        print(f"Loaded: {file_path}")
        # Embed the input text in batches of no more than MAX_TOKENS_PER_BATCH tokens each
        input_text_list = df_chunks.iloc[:, 1].tolist()
        num_tokens = sum(len(text.split()) for text in input_text_list)
        print("Embedding " + str(num_tokens) + " tokens")
        if num_tokens > MAX_TOKENS_PER_BATCH:
            # If there are more than MAX_TOKENS_PER_BATCH tokens, split the input text into batches and send each batch in a separate request
            embeddings = []
            input_text_batch = []
            for text in input_text_list:
                if sum(len(batch_text.split()) for batch_text in input_text_batch) + len(text.split()) > MAX_TOKENS_PER_BATCH:
                    # If the current batch would exceed MAX_TOKENS_PER_BATCH tokens, send the current batch and start a new batch
                    embeddings_batch = embed_input_text(input_text_batch)
                    embeddings.extend(embeddings_batch)
                    input_text_batch = []
                    print(f"Waiting 1 minute before sending next batch...")
                    time.sleep(60)
                input_text_batch.append(text)
            if input_text_batch:
                # Send the final batch if it is not empty
                embeddings_batch = embed_input_text(input_text_batch)
                embeddings.extend(embeddings_batch)
        else:
            # If there are fewer than or equal to MAX_TOKENS_PER_BATCH tokens, embed all the text in one request
            embeddings = embed_input_text(input_text_list)

        # Extract the actual embeddings from the list of dictionaries and stack them to form a 2D numpy array
        embeddings_array = np.vstack([np.array(e['embedding']) for e in embeddings])
        # Save the embeddings_array to the output_folder subfolder
        # Remove the file extension from the filename
        filename_without_extension = os.path.splitext(file)[0]
        npy_filename = f"{filename_without_extension}.npy"
        output_path = os.path.join(output_folder, npy_filename)
        np.save(output_path, embeddings_array)