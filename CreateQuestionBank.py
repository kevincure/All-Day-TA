# Create a bank of multiple choice questions
# Run at command line and it will give you options
# This is a very difficult task - maybe half are good, 40% are true but boring, 10% are wrong
# CleanQuestionBank lets you scroll these and auto-delete before students see them

import os
import time
import nltk
import pandas as pd
import numpy as np
import json
import io
import re
import openai

# load user settings and api key
def read_settings(file_name):
    settings = {}
    with open(file_name, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            settings[key] = value
    return settings
settings = read_settings("settings.txt")
dataname="textchunks"
filedirectory = settings["filedirectory"]
classname = settings["classname"]
professor = settings["professor"]
assistants = settings["assistants"]
classdescription = settings["classdescription"]
assistant_name = settings['assistantname']
instruct = settings['instructions']
num_chunks = int(settings['num_chunks'])
# get API_key
with open("APIkey.txt", "r") as f:
    openai.api_key = f.read().strip()
# Check if the subfolder exists, if not, create it
output_folder = "Question Bank"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

df_chunks = pd.read_csv(dataname+"-originaltext.csv")
embedding = np.load(dataname+".npy")

output_file = os.path.join(output_folder, "questionbank.csv")

# Find existing unique top-level topics
def get_unique_topics(csv_file):
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file, header=None)
        return df[1].unique().tolist()  # Assuming overall_topic is in the first column
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
unique_topics = get_unique_topics(output_file)
print(unique_topics)
# Prompt user for overall_topic
if unique_topics:
    overall_topic = get_user_input("Enter high-level topic: ", unique_topics)
    if overall_topic.lower() == 'new':
        overall_topic = input("Enter new high-level topic: ")
else:
    overall_topic = input("Enter new high-level topic: ")

# Prompt user for question_topic, including multiple at once
question_topics_input = input("Enter specific subtopic(s). If you enter more than one, separate them with a comma. Be as specific as possible; the system will generate three questions for each subtopic: ")
question_topics = [topic.strip() for topic in question_topics_input.split(',')]

# Process new_questions for each question topic
for question_topic in question_topics:
    embedthequery = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=question_topic
    )
    query_embed=embedthequery["data"][0]["embedding"]

    # function to compute dot product similarity; tested using Faiss library and didn't really help
    def compute_similarity(embedding, userquery):
       similarities = np.dot(embedding, userquery)
       return similarities

    # compute similarity for each row and add to new column
    df_chunks['similarity'] = np.dot(embedding, query_embed)
    # sort by similarity in descending order
    df_chunks = df_chunks.sort_values(by='similarity', ascending=False)
    # Select the top 8 most similar articles
    most_similar_df = df_chunks.head(8)
    most_similar = '\n\n'.join(row[1] for row in most_similar_df.values)

    # generate questions
    instructions = "You are a very truthful, precise TA in a " + classname + ".  You think step by step. A strong graduate student is using you as a tutor.  The student would like you to prepare a multiple choice question on the requested topic drawing ONLY on the attached context. The concepts and definitions used to answer the questions MUST come DIRECTLY from the attached context. It should be a definitional question, though not necessarily just asking for the definition of the primary concept in the attached context (instead, e.g., 'Why is X not a good example of Y', '1. Which of the following is an example of Z'). If the requested topic has two parts, make sure the questions require student knowledge of both aspects. NEVER refer to 'the attached context' or 'according to the article' or similar. Assume the student has no idea what context you are drawing your question from, and NEVER state the context you are drawing the question from.  Return the question in the following format: the question, line break (NOT A PARAGRAPH BREAK!), four options 'A)' to 'D)' (with a line break after each), the letter of the correct answer by itself, line break, a VERY DETAILED explanation of why it is correct based on the context, line break (NOT A PARAGRAPH BREAK), a LENGTHY AND COMPLETE MANY SENTENCE explanation of all possible student mistakes for EACH wrong answer based on the context of why it is wrong. Before starting the 2nd and 3rd questions and answers, place a paragraph break. Separate components of each individual question/answer with LINE BREAKS. FOR EACH QUESTION, THINK STEP BY STEP AND CONFIRM THAT ALL DETAIL NEEDED TO ANSWER THE QUESTION GIVEN THE CONTEXT IN INCLUDED IN EACH QUESTION."
    original_question = "Construct a VERY CHALLENGING multiple-choice question to test me on " + question_topic + " in the broader context of the concept of " + overall_topic + "."
    print("Preparing first question related to: " + question_topic)
    send_to_gpt = []
    send_to_gpt.append({"role": "system", "content": instructions + "The relevant context from class is: " + most_similar})
    send_to_gpt.append({"role": "user", "content": original_question})
    response = openai.ChatCompletion.create(
        messages=send_to_gpt,
        temperature=0.2,
        model = "gpt-4-1106-preview"
    )
    new_questions=response["choices"][0]["message"]["content"]
    print("Questions generated")
    tokens_sent = response["usage"]["prompt_tokens"]
    tokens_sent2 = response["usage"]["completion_tokens"]
    print(f"GPT4 Response gathered with proper html. You used {tokens_sent} prompt and {tokens_sent2} completion tokens.")

    instructions2 = "You are a very truthful, precise TA in a " + classname + ".  You think step by step. A strong graduate student is using you as a tutor.  The student would like you to prepare a multiple choice question on the requested topic drawing ONLY on the attached context. The concepts and definitions used to answer the questions MUST come DIRECTLY from the attached context, though you may be creative in setting up vignettes. Your question should not simply be about a definition, but should be an MBA LEVEL conceptual question requiring application of the requested topic to a difficult decision (ex: 'X and Y are both methods of performing Z. Epic Systems is trying to do such-and-such. Why...). If the requested topic has two parts, make sure the questions require student knowledge of both aspects. NEVER refer to 'the attached context' or 'according to the article' or similar. Assume the student has no idea what context you are drawing your question from, and NEVER state the context you are drawing the question from.  Return the questions in the following format: the question, line break (NOT A PARAGRAPH BREAK!), four options 'A)' to 'D)' (with a line break after each), the letter of the correct answer by itself, line break, a VERY DETAILED PARAGRAPH LENGTH explanation of why it is correct based on the context, line break (NOT A PARAGRAPH BREAK), a LENGTHY AND COMPLETE MANY SENTENCE explanation of all possible student mistakes for EACH wrong answer based on the context of why it is wrong. THINK STEP BY STEP AND CONFIRM THAT ALL DETAIL NEEDED TO ANSWER THE QUESTION GIVEN THE CONTEXT IS INCLUDED IN EACH QUESTION."
    original_question2 = "Construct a VERY CHALLENGING multiple-choice question to test me on " + question_topic + " in the broader context of the concept of " + overall_topic + "."
    print("Preparing second question related to: " + question_topic)
    send_to_gpt = []
    send_to_gpt.append(
        {"role": "system", "content": instructions2 + "The relevant context from class is: " + most_similar})
    send_to_gpt.append({"role": "user", "content": original_question2})
    response = openai.ChatCompletion.create(
        messages=send_to_gpt,
        temperature=0.2,
        model="gpt-4-1106-preview"
    )
    new_questions2 = response["choices"][0]["message"]["content"]
    print("Questions generated")
    tokens_sent3 = response["usage"]["prompt_tokens"]
    tokens_sent4 = response["usage"]["completion_tokens"]
    print(f"GPT4 Response gathered with proper html. You used {tokens_sent3} prompt and {tokens_sent4} completion tokens.")

    instructions3 = "You are a very truthful, precise TA in a " + classname + ".  You think step by step. A strong graduate student is using you as a tutor.  The student would like you to prepare a multiple choice question on the requested topic drawing ONLY on the attached context. The concepts and definitions used to answer the questions MUST come DIRECTLY from the attached context, though you may be creative in setting up vignettes. Your question should be an MBA LEVEL Harvard Business School-type DETAILED VIGNETTE about some new company in a new industry whose problem requires subtle application of the requested topic to a difficult decision (ex: 'The CEO of Canadian Pacific was considering issue X, when...). If the requested topic has two parts, make sure the questions require student knowledge of both aspects. NEVER refer to 'the attached context' or 'according to the article' or similar. Assume the student has no idea what context you are drawing your question from, and NEVER state the context you are drawing the question from.  Return the questions in the following format: the question, line break (NOT A PARAGRAPH BREAK!), four options 'A)' to 'D)' (with a line break after each), the letter of the correct answer by itself, a VERY DETAILED PARAGRAPH LENGTH explanation of why it is correct based on the context, line break (NOT A PARAGRAPH BREAK), a LENGTHY AND COMPLETE MANY SENTENCE explanation of all possible student mistakes for EACH wrong answer based on the context of why it is wrong. THINK STEP BY STEP AND CONFIRM THAT ALL DETAIL NEEDED TO ANSWER THE QUESTION GIVEN THE CONTEXT IS INCLUDED IN EACH QUESTION."
    original_question3 = "Construct a VERY CHALLENGING multiple-choice question to test me on " + question_topic + " in the broader context of the concept of " + overall_topic + "."
    print("Preparing third question related to: " + question_topic)
    send_to_gpt = []
    send_to_gpt.append(
        {"role": "system", "content": instructions3 + "The relevant context from class is: " + most_similar})
    send_to_gpt.append({"role": "user", "content": original_question3})
    response = openai.ChatCompletion.create(
        messages=send_to_gpt,
        temperature=0.2,
        model="gpt-4-1106-preview"
    )
    new_questions3 = response["choices"][0]["message"]["content"]
    print("Questions generated")
    tokens_sent5 = response["usage"]["prompt_tokens"]
    tokens_sent6 = response["usage"]["completion_tokens"]
    print(f"GPT4 Response gathered with proper html. You used {tokens_sent3} prompt and {tokens_sent4} completion tokens.")

    output_file = os.path.join(output_folder, "questionbank.csv")
    # Writing the string to the question file, w/o overwriting old questions
    # Split the string into paragraphs and then into components
    # Step 1: Remove existing paragraph breaks
    new_questions = new_questions.replace('\n\n', '\n')
    new_questions2 = new_questions2.replace('\n\n', '\n')
    new_questions3 = new_questions3.replace('\n\n', '\n')
    new_questions = new_questions + "\n\n" + new_questions2 + "\n\n" + new_questions3

    # Step 3: Split into rows on paragraph breaks, then into columns on line breaks
    rows = [["Not checked yet", overall_topic, question_topic, most_similar] + row.split('\n') for row in new_questions.split('\n\n') if row.strip()]

    # Convert to a DataFrame, and paste all explanations to column 12 if it got the format wrong
    df = pd.DataFrame(rows)
    if df.shape[1] > 12:
        df[11] = df.iloc[:, 11:].apply(lambda x: ' '.join(x.dropna().astype(str)), axis=1)
        df = df.iloc[:, :12]

    # Append to CSV
    df.to_csv(output_file, mode='a', index=False, header=False, encoding='utf-8')
    print("Saving questions on " + question_topic)






