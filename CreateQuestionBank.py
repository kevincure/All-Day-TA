# Use once your Virtual TA is set up to create a bank of multiple choice questions using AI
# The AI will also save explanations of right and wrong answers, and will draw directly from your content
# Run at command line and it will give you options 
# This is a very difficult task - maybe half are good, 40% are true but boring, 10% are wrong
# See readme.md for best practices

import os
import time
import pandas as pd
import numpy as np
import re
import openai
import csv
import nltk
import json
nltk.download('punkt', quiet=True)  # Download necessary tokenizer data if not already present
from nltk.tokenize import word_tokenize
import cohere

# load user settings and api key
def read_settings(file_name):
    settings = {}
    with open(file_name, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            settings[key] = value
    return settings
settings = read_settings("settings.txt")
classname = settings["classname"]
# Check if the subfolder exists, if not, create it
output_folder = "Question Bank"
os.makedirs(output_folder, exist_ok=True)
output_file = os.path.join(output_folder, "questionbank.csv")

# get API_key
with open("APIkey.txt", "r") as f:
    openai.api_key = f.read().strip()
# Get Cohere key
with open("CohereAPI.txt", "r") as f:
    cohere.api_key = f.read().strip()
co = cohere.Client(cohere.api_key)
print("Application settings loaded")

# this queries OpenAI
def query_openai(content, max_tokens, model, temperature, instructions=None):
    # Sends a query to OpenAI's GPT model and returns the first message content from the response.
    # Parameters: content (str): The content to send as the user's message, max_tokens (int): The maximum number of tokens to generate in the completion, model (str): The model to use for the completion (e.g., "gpt-4"), temperature (float): The temperature setting for the completion, controlling randomness.
    # Returns: str: The content of the first message in the response.
    attempt = 0
    while attempt < 3:
        try:
            send_to_gpt = [{"role": "user", "content": content}]
            if instructions is not None:
                send_to_gpt.append({"role": "system", "content": instructions})
            # Make the API call
            response = openai.ChatCompletion.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=send_to_gpt
            )
            tokens_sent = response["usage"]["prompt_tokens"]
            tokens_sent2 = response["usage"]["completion_tokens"]
            print(f"{model} responded. You used {tokens_sent} prompt and {tokens_sent2} completion tokens.")
            # Extract and return the first response content
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"An error occurred: {e}")
            attempt += 1
            if attempt < 3:
                print("Waiting 30 seconds before retrying...")
                time.sleep(30)  # Wait for 30 seconds before the next attempt
            else:
                print("Maximum attempts reached to use API. Exiting.")

# function to embed queries; can use a better embedding in future if it develops
def embed(query):
    embed_raw = openai.Embedding.create(model="text-embedding-ada-002", input=query)
    embedthequery = embed_raw["data"][0]["embedding"]
    return embedthequery

# function to compute dot product similarity; tested using Faiss library and didn't really help
def compute_similarity(embedding, userquery):
    similarities = np.dot(embedding, userquery)
    return similarities

# function to rerank using Cohere - this improves over cos similarity but is too slow to use overall
# it works on 15 languages as of Feb 2024
# this uses the fact that every chunk starts Source: name of document.
def rerank(query, chunks_to_rerank):
    rerank_docs = co.rerank(query, chunks_to_rerank, model="rerank-multilingual-v2.0")
    rerank_df = pd.DataFrame([{'Title': doc.document['text'].split(':', 1)[1].split('.', 1)[0], 'Text': doc.document['text'], 'similarity': doc.relevance_score} for doc in rerank_docs])
    return rerank_df

# timekeeping
def timecheck(start_time, description):
    print(f"{description}. Total time taken: {time.time() - start_time:.2f} seconds")

# Function to load data
def load_data():
    df_chunks = pd.read_csv("textchunks-originaltext.csv")
    embedding = np.load("textchunks.npy")
    return df_chunks, embedding

def append_to_csv(input_string, overall_topic, question_topic):
    # Attempt to fix common JSON formatting issues and remove unexpected text
    corrected_string = input_string.strip()
    # Add opening and closing square brackets if missing
    if not corrected_string.startswith('['):
        corrected_string = '[' + corrected_string
    if not corrected_string.endswith(']'):
        corrected_string = corrected_string + ']'

    # Remove text that is not part of JSON structure
    # This regex replaces occurrences of text that do not match JSON object boundaries with commas
    corrected_string = re.sub(r'\}\s*([^{,\]]+)\s*\{', '},{', corrected_string)
    corrected_string = re.sub(r'\[\s*([^{,\]]+)\s*\{', '[{', corrected_string)
    corrected_string = re.sub(r'\}\s*([^{,\]]+)\s*\]', '}]', corrected_string)

    try:
        data = json.loads(corrected_string)
        # Verify each entry has exactly 9 keys
        if all(isinstance(item, dict) and len(item) == 9 for item in data):
            with open(output_file, 'a', newline='', encoding='utf-8') as file:
                csv_writer = csv.writer(file)
                for item in data:
                    row = [overall_topic, question_topic] + list(item.values())
                    csv_writer.writerow(row)
            return True
        else:
            try_to_fix_json_query = "The following is meant to be a json query, with three entries of nine keys each, but it has errors. Rewrite it correcting any errors such as missing brackets or text between keys. Return ONLY the json. Here is the prior attempt for you to correct: " + corrected_string
            try_to_fix_json = query_openai(try_to_fix_json_query, 4000, "gpt-4", 0.2)
            data2 = json.loads(try_to_fix_json)
            # Verify each entry has exactly 9 keys
            if all(isinstance(item, dict) and len(item) == 9 for item in data2):
                with open(output_file, 'a', newline='', encoding='utf-8') as file:
                    csv_writer = csv.writer(file)
                    for item in data2:
                        row = [overall_topic, question_topic] + list(item.values())
                        csv_writer.writerow(row)
                return True
            else:
                # Not valid JSON
                print("Attempted to fix json but still not working. Final try: " + try_to_fix_json + "First try: " + input_string)
                print(f"Error parsing JSON: {e}")
                return False
    except ValueError as e:
        try_to_fix_json_query = "The following is meant to be a json query, with three entries of nine keys each, but it has errors. Rewrite it correcting any errors such as missing brackets or text between keys. Return ONLY the json. Here is the prior attempt for you to correct: " + corrected_string
        try_to_fix_json = query_openai(try_to_fix_json_query, 4000, "gpt-4", 0.2)
        data2 = json.loads(try_to_fix_json)
        # Verify each entry has exactly 9 keys
        if all(isinstance(item, dict) and len(item) == 9 for item in data2):
            with open(output_file, 'a', newline='', encoding='utf-8') as file:
                csv_writer = csv.writer(file)
                for item in data2:
                    row = [overall_topic, question_topic] + list(item.values())
                    csv_writer.writerow(row)
            return True
        else:
            # Not valid JSON
            print("Attempted to fix json but still not working. Final try: " + try_to_fix_json + "First try: " + input_string)
            print(f"Error parsing JSON: {e}")
            return False

# Find existing unique top-level topics
def get_unique_topics(csv_file):
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file, header=None)
        return df[0].unique().tolist()  # Assuming overall_topic is in the first column
    return []

# Ask for lower-level topic
def get_user_input(prompt, options):
    if options:
        print("Enter a number to choose from the following options:")
        print("[1] Add a new high-level topic")
        for i, option in enumerate(options, start=2):
            print(f"[{i}] {option}")
        user_input = input(prompt)
        if user_input.isdigit() and int(user_input) == 1:
            return 'new'
        elif user_input.isdigit() and 2 <= int(user_input) <= len(options) + 1:
            return options[int(user_input) - 2]
        else:
            print("Invalid input. Please try again.")
            return get_user_input(prompt, options)
    else:
        user_input = input(prompt)
        return get_user_input(prompt, options)

# Get unique overall_topic values
start_time = time.time()  # record the start time
unique_topics = get_unique_topics(output_file)
print(unique_topics)
# Prompt user for overall_topic
if unique_topics:
    overall_topic = get_user_input("Enter a number from those options: ", unique_topics)
    if overall_topic.lower() == 'new':
        overall_topic = input("Enter new high-level topic: ")
else:
    overall_topic = input("Enter new high-level topic: ")
# Prompt user for question_topic, including multiple at once
question_topic = input("Enter a specific subtopic(s). Be as specific as possible; the system will generate three questions for this subtopic: ")
timecheck(start_time, "Start writing the three questions")

content_definitions = f"Consider the topic '{question_topic}' a student is studying in their course. Are there any unclear acronyms or phrases IN THAT TOPIC you need to understand which may depend specifically on details of this course? Return a single acronyms, terms, or concepts you want a definition of. Say nothing else."
response_definitions = query_openai(content_definitions, 50, "gpt-4", 0.0)
print("Definitions needed? " + response_definitions)
terms = response_definitions.split(",")
if len(terms) > 1:
    print("Error getting definitions: More than two phrases provided.")
else:
    # Loop through each term, pass it to llm for definitions, collect the results
    definitions = []
    for term in terms:
        term_chunks = pd.read_csv("textchunks-originaltext.csv")
        term_full_embedding = np.load("textchunks.npy")
        term_question = f"What is/are {term} in the context of {overall_topic}?"
        term_embed = embed(term_question)
        # compute dot_product similarity for each row and add to new column
        term_chunks['similarity'] = compute_similarity(term_full_embedding, term_embed)
        # sort by similarity in descending order
        term_chunks = term_chunks.sort_values(by='similarity', ascending=False)
        # construct reranking
        rerank_term_df = rerank(term_question, term_chunks.head(1000)['Raw Text'])
        print(rerank_term_df.head(4))
        # Select the most similar chunks
        most_similar_term_rerank_df = rerank_term_df.head(4)
        most_similar_term_rerank = '\n\n'.join(row[1] for row in most_similar_term_rerank_df.values)
        instructions_terms = "You are a very truthful, precise TA in a " + classname + ".  You think step by step. A strong graduate student is asking questions. The answer may appear in the attached selections from class-related book chapters, handouts, transcripts, and articles. In your answer, do not restate the question, do not apologize and NEVER REFER TO 'attached context' or `attached information'. When answering the student, ONLY USE DEFINITIONS, ACRONYM DEFINITIONS, CONCEPTS, IDEAS FROM THE ATTACHED COURSE DOCUMENTS. Do not guess about the meaning of an acronym or technical term unless its stated in the attached context. If the attached context contains the definitions and information you need to answer the student question, in no more than three paragraphs answer it; Be VERY CAREFUL TO MATCH THE TERMINOLOGY AND DEFINITIONS, implicit or explicit, in the attached context, AND USE ONLY THEM."
        explain_terms = "Question: what does " + term + " mean or stand for? Snippets of course content: " + most_similar_term_rerank
        definitions.append("\n\n" + query_openai(explain_terms, 1000, "gpt-4", 0.2, instructions_terms))
    # Combine the returned strings into one
    combined_definitions = "Definitions and meanings: " + ", ".join(definitions)
    # Output the combined string
    print(combined_definitions)
    timecheck(start_time, "Definitions and concepts gathered")

# load class text and embeddings (CHANGE TO USE 'CORE' TEXT LATER)
df_chunks = pd.read_csv("textchunks-originaltext.csv")
embedding = np.load("textchunks.npy")
original_question = "Explain in detail " + question_topic
# Embed 'original_question', the user query modified to handle syllabus Qs and followups
query_embed = embed(original_question)
print("Query we embed is: " + original_question)
# compute dot_product similarity for each row and add to new column
df_chunks['similarity'] = compute_similarity(embedding, query_embed)
# sort by similarity in descending order
df_chunks = df_chunks.sort_values(by='similarity', ascending=False)
# construct reranking of top 1000
rerank_df = rerank(original_question, df_chunks.head(1000)['Raw Text'])
# Select the most similar chunks
most_similar_rerank_df = rerank_df.head(16)
# Count the number of occurrences of each title in most_similar_df
title_counts = most_similar_rerank_df['Title'].value_counts()
title_df = pd.DataFrame({'Title': title_counts.index, 'Count': title_counts.values}).sort_values('Count', ascending=False)
title_df_filtered = title_df[title_df['Count'] >= 1]
print(title_df_filtered)
timecheck(start_time, "Query similarity sorted and reranked")
most_similar_rerank = '\n\n'.join(row[1] for row in most_similar_rerank_df.values)
most_similar_rerank = combined_definitions + '\n\n' + most_similar_rerank
instructions = "You are a very truthful, precise TA in a " + classname + ".  You think step by step. A strong graduate student is asking questions. The answer may appear in the attached selections from class-related book chapters, handouts, transcripts, and articles. In your answer, do not restate the question, do not apologize and NEVER REFER TO 'attached context' or `attached information'. ONLY USE DEFINITIONS, ACRONYM DEFINITIONS, CONCEPTS, IDEAS FROM THE ATTACHED COURSE DOCUMENTS. Do not guess about the meaning of an acronym or technical term unless its stated in the attached context. In eight paragraphs answer the question, giving as much detail, caveats, clarity and explanation as you can. Be VERY CAREFUL TO MATCH THE TERMINOLOGY AND DEFINITIONS, implicit or explicit, in the attached context, AND USE ONLY THEM. Remember, you are a precise TA who wants the student to understand but also wants to make sure you do not contradict the readings and lectures the student has been given in class."
content = "Question: " + original_question + " Snippets of course content: " + most_similar_rerank
response_preamble = query_openai(content, 2000, "gpt-4-turbo-preview", 0.2, instructions)

instructions = "Output format a json with 9 keys for each question. The entire set of three questions should be valid json, including comma separation between rows and opening and closing brackets. The entries are Question:, Correct Answer:, First Incorrect Answer:, Second Incorrect Answer:, Third Incorrect Answer:, Detailed Explanation of Correct Answer:, Full Paragraph Explanation of First Incorrect Answer:, Full Paragraph Explanation of Second Incorrect Answer:, Full Paragraph Explanation of Third Incorrect Answer. DO NOT label or letter entries or talk about 'option 1', 'C)', etc."
content = "Construct three VERY CHALLENGING multiple-choice questions (that is, at the level of a graduate class) to test a student on '" + question_topic + "' using ONLY the attached content. Use the precise definitions you observe to create the questions. One question should be definitional (though not simply 'what is the definition of x'), one should involve a vignette where you may creatively name any people, companies, agents, etc. taking part, and one should be a question about a deeper aspect of the main topic or some related aspect.  The content you should draw from is: " + response_preamble
response_question = query_openai(content, 2000, "gpt-4", 0.2, instructions)
is_valid = append_to_csv(response_question, overall_topic, question_topic)
if is_valid:
    print("The data was appended to the question bank successfully.")
else:
    print("The input was not valid JSON with 9 keys per entry.")
instructions = "Output format a json with 9 keys for each question. The entire set of three questions should be valid json, including comma separation between rows and opening and closing brackets. The entries are Question:, Correct Answer:, First Incorrect Answer:, Second Incorrect Answer:, Third Incorrect Answer:, Detailed Explanation of Correct Answer:, Full Paragraph Explanation of First Incorrect Answer:, Full Paragraph Explanation of Second Incorrect Answer:, Full Paragraph Explanation of Third Incorrect Answer. DO NOT label or letter entries or talk about 'option 1', 'C)', etc."
content = "Construct three VERY CHALLENGING multiple-choice questions (that is, at the level of a graduate class) to test a student on '" + question_topic + "' using ONLY the attached content. Use the precise definitions you observe to create the questions. One question should ask for a pure definition, one should involve a real-world application of this concept using specific real agents applying a concept related to this topic, and one should be a question about the relation of the main topic and something else in the attached content.  The content you should draw from is: " + response_preamble
response_question = query_openai(content, 2000, "gpt-4", 0.4, instructions)
is_valid = append_to_csv(response_question, overall_topic, question_topic)
if is_valid:
    print("The data was appended to the question bank successfully.")
else:
    print("The input was not valid JSON with 9 keys per entry.")
