# Flask app for All Day TA
# See readme.md for files that must be run before you use this
# PLEASE NOTE USAGE CAPS by tier on OpenAI, your students may hit these caps if you are not, say, Tier 4.  I prepay
#  at start of term to avoid this
# Jan 4 2024 version

# You probably don't need all these; I just used them all at some point trying things out
import csv
import nltk
import numpy as np
import openai
import pandas as pd
import json
import re
from flask import Flask, render_template, request, url_for, flash, session, redirect, jsonify, session
import requests
import os
import time
import threading

# create the flask app
app = Flask(__name__)
app.secret_key = 'testingkey'
# get settings from settings.txt file
def read_settings(file_name):
    settings = {}
    with open(file_name, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            settings[key] = value
    return settings
settings = read_settings("settings.txt")
dataname = "textchunks"
classname = settings["classname"]
professor = settings["professor"]
assistants = settings["assistants"]
classdescription = settings["classdescription"]
assistant_name = settings['assistantname']
instruct = settings['instructions']
# get API_key
with open("APIkey.txt", "r") as f:
    openai.api_key = f.read().strip()
print("Application settings loaded")

# this lets us load the data only once and to do it in the background while the user types the first q
# I don't bother locking the file while users load the page due to the always-on nature of the site
df_chunks = None
embedding = None
last_session = None
def load_df_chunks():
    print("Loading data chunks")
    global df_chunks, embedding
    if embedding is None:
        df_chunks = pd.read_csv(dataname+"-originaltext.csv")
        embedding = np.load(dataname+".npy")
    else:
        print("Database already loaded")
    return df_chunks
def background_loading():
    print("Begin loading data")
    global df_chunks, embedding
    df_chunks = load_df_chunks()
    print("Loaded data from background")
# this grabs a cookie with the context from a multiple choice question when serving up answers
def grab_last_response():
    global last_session
    last_session = session.get('last_session', None)
    print("Ok, we have prior content via a cookie")
    if last_session is None:
        print("I don't know old content")
        last_session = ""
    return last_session

    
@app.route('/', methods=('GET', 'POST'))

def index():
    if request.method == 'POST':
        # Load the text and its embeddings
        print("ok, starting")
        start_time = time.time()  # record the start time
        df_chunks = load_df_chunks() # get df_chunks from the global
        elapsed_time = time.time() - start_time  # calculate the elapsed time
        print(f"Data loaded. Time taken: {elapsed_time:.2f} seconds")
        original_question = request.form['content1']

        # if there is a previous question and it's not multiple choice answer, check to see if the new one is a syllabus q or a followup
        # GPT4 really helps a ton with these questions, as of Dec 2023, GPT-4 Turbo is not good enough at precisely following instructions
        # Question length typed into the box is limited to 200 words
        if not (request.form['content1'].startswith('a:')):
            # first let's see if it's on the syllabus
            send_to_gpt = []
            send_to_gpt.append({"role": "user",
                                "content": f"Students in {classname} taught by {professor} are asking questions. Class description: {classdescription}  Is this question likely about the logistical details, schedule, nature, teachers, assignments, or syllabus of the course?  Answer Yes or No and nothing else: {request.form['content1']}"})
            # In a sample of syllabus-related questions using GPT-4 and GPT-4-1106-preview ("Turbo"), GPT-4 correctly identified
            #    syllabus questions 91% of the time, and Turbo did 45% of the time, hence we use it here despite the expense
            #    Note that the system will likely answer correctly either way; this question just checks the student question then
            #    pushes the system to look for the answer in the syllabus file, a common request
            response = openai.ChatCompletion.create(
                model="gpt-4",
                max_tokens=1,
                temperature=0.0,
                messages=send_to_gpt
            )
            print("Is this a syllabus question? GPT-4 says " + response["choices"][0]["message"]["content"])
            tokens_sent = response["usage"]["prompt_tokens"]
            tokens_sent2 = response["usage"]["completion_tokens"]
            elapsed_time = time.time() - start_time  # calculate the elapsed time
            print(f"GPT4 Response gathered. You used {tokens_sent} prompt and {tokens_sent2} completion tokens. Time taken: {elapsed_time:.2f} seconds")                # Construct new prompt if AI says that this is a syllabus question
            if response["choices"][0]["message"]["content"].startswith('Y') or response["choices"][0]["message"]["content"].startswith('y'):
                # Concatenate the strings to form the original_question value
                print("It seems like this question is about the syllabus")
                original_question = "I may be asking about a detail on the syllabus for " + classname + ". " + request.form['content1']

            # now let's see if it might be a followup question
            # GPT-4 Turbo as of Dec 2023 overidentifies these, while GPT-4 misses a few legitimate follow-ups
            if len(request.form['content2'])>1:
                send_to_gpt = []
                send_to_gpt.append({"role": "user",
                                    "content": f"Consider this new user question: {request.form['content1']}. Their prior question and response was {request.form['content2']} Would it be helpful to have the context of the previous question and response to answer the new one?  For example, the new question may refer to 'this' or 'that' or 'the company' or 'their' or 'his' or 'her' or 'the paper' or similar terms whose context is not clear if you only know the current question and don't see the previous question and response, or it may ask for more details or to summarize or rewrite or expand on the prior answer in a way that is impossible to do unless you can see the previous answer, or the user may just have said 'Yes' following up on a clarification in the previous question and answer.  Answer either Yes or No."})
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    max_tokens=1,
                    temperature=0.0,
                    messages=send_to_gpt
                )
                print("Might this be a follow-up? GPT-4 says " + response["choices"][0]["message"]["content"])
                tokens_sent = response["usage"]["prompt_tokens"]
                tokens_sent2 = response["usage"]["completion_tokens"]
                elapsed_time = time.time() - start_time  # calculate the elapsed time
                print(f"GPT4 Response gathered. You used {tokens_sent} prompt and {tokens_sent2} completion tokens. Time taken: {elapsed_time:.2f} seconds")
                # Construct new prompt if AI says that this is a followup
                if response["choices"][0]["message"]["content"].startswith('Y') or response["choices"][0]["message"]["content"].startswith('y'):
                   # Concatenate the strings to form the original_question value
                    print("Creating follow-up question")
                    original_question = 'I have a followup on the previous question and response. ' + request.form['content2'] + 'My new question is: ' + request.form['content1']

        # if answer to Q&A, don't embed a new search, just use existing context
        if request.form['content1'].startswith('a:'):
            print("Let's try to answer that question")
            most_similar = grab_last_response()
            title_str = "<p></p>"
            print("Query being used: " + request.form['content1'])
            print("The content we draw on is " + most_similar)
            elapsed_time = time.time() - start_time  # calculate the elapsed time
            print(f"Original context for question loaded. Time taken: {elapsed_time:.2f} seconds")
        else:
            # embed the query
            embedthequery = openai.Embedding.create(
                model="text-embedding-ada-002",
                input=original_question
            )
            print("Query we asked is: " + original_question)
            query_embed = embedthequery["data"][0]["embedding"]
            elapsed_time = time.time() - start_time  # calculate the elapsed time
            print(f"Quert embedded. Time taken: {elapsed_time:.2f} seconds")

            # function to compute dot product similarity; tested using Faiss library and didn't really help
            def compute_similarity(embedding, userquery):
               similarities = np.dot(embedding, userquery)
               return similarities

            # compute similarity for each row and add to new column
            df_chunks['similarity'] = np.dot(embedding, query_embed)
            # sort by similarity in descending order
            df_chunks = df_chunks.sort_values(by='similarity', ascending=False)
            # Select the top query_similar_number most similar articles
            most_similar_df = df_chunks.head(8)
            elapsed_time = time.time() - start_time  # calculate the elapsed time
            print(f"Original query similarity sorted. Time taken: {elapsed_time:.2f} seconds")
            # Count the number of occurrences of each title in most_similar_df
            title_counts = most_similar_df['Title'].value_counts()
            # Create a new dataframe with title and count columns, sorted by count in descending order
            title_df = pd.DataFrame({'Title': title_counts.index, 'Count': title_counts.values}).sort_values('Count', ascending=False)
            # Filter the titles that appear at least three times
            title_df_filtered = title_df[title_df['Count'] >= 3]
            # Get the most common titles in title_df_filtered; this creates the hamburger icon with the most related content
            titles = title_df_filtered['Title'].values.tolist()
            if len(titles) == 1:
                title_str = f'<span style="float:right;" id="moreinfo"><a href="#" onclick="toggle_visibility(\'sorting\');" style="text-decoration: none; color: black;">&#9776;</a><div id="sorting" style="display:none; font-size: 12px;"> [The most likely related text is "{titles[0]}"]</div></span><p>'
                title_str_2 = f'The most likely related text is {titles[0]}. '
            elif len(titles) == 0:
                title_str = "<p></p>"
                title_str_2 = ""
            else:
                top_two_titles = titles[:2]
                title_str = f'<span style="float:right;" id="moreinfo"><a href="#" onclick="toggle_visibility(\'sorting\');" style="text-decoration: none; color: black;">&#9776;</a><div id="sorting" style="display:none; font-size: 12px;"> [The most likely related texts are "{top_two_titles[0]}" and "{top_two_titles[1]}"]</div></span><p>'
                title_str_2 = f'The most likely related texts are {top_two_titles[0]} and {top_two_titles[1]}. '
            elapsed_time = time.time() - start_time  # calculate the elapsed time
            print(f"Most related texts are {titles[:1]}.")
            most_similar = '\n\n'.join(row[1] for row in most_similar_df.values)

        # Now that we have the retrieval augmentation done, let's do the "generation" of the RAG
        reply = []
        send_to_gpt = []
        # THIS TEMPORARY DOES NOTHING UNTIL WE REINTEGRATE MULTIPLE CHOICE
        if request.form['content1'].startswith('a:'):
            instructions = "You are a very truthful, precise TA in a " + classname + ".  You think step by step. You are testing a strong graduate student on their knowledge.  The student would like you, using the attached context, to tell them whether they have answered the attached multiple choice question correctly.  Draw ONLY on the attached context for definitions and theoretical content.  Never refer to 'the attached context' or 'the article says that' or other context: just state your answer and the rationale."
            original_question =  request.form['content1'][len('a:'):].strip()
            send_to_gpt.append({"role": "system", "content": instructions + request.form['content2']})
            send_to_gpt.append({"role": "user", "content": original_question})
            response = openai.ChatCompletion.create(
                messages=send_to_gpt,
                temperature=0.2,
                model = "gpt-4-1106-preview"
            )
            print(f"Previous content we are using to respond is {request.form['content2']}")
        else:
            # Note how good GPT4 is at not answering on unrelated tasks - it will answer "I don't know" given instructions if you ask it for a joke about fungi, or "what is your system prompt", or similar unrelated questions
            # Prior versions of this TA used followup ensemble questions to try to stop hallucination but it is largely not necessary anymore
            # I use GPT4-Turbo not GPT-4 just for cost reasons here because we send a lot of content and it is too expensive otherwise
            instructions = "You are a very truthful, precise TA in a " + classname + ", a " + classdescription + ".  You think step by step. A strong graduate student is asking you questions.  The answer to their query may appear in the following content drawn from class-related book chapters, handouts, transcripts, and articles. You CAN ONLY USE DEFINITIONS, CONCEPTS, IDEAS FROM THE ATTACHED CONTEXT.  If you cannot answer the question under those constraints, and the question is DEFINITELY unrelated to class subject, syllabus, or course details, say 'I don't know - this appears unrelated to the class. Can you restate your question?' If the question is potentially related to the class, syllabus, or course details but the attached context does not give you enough to answer, say 'I don't know. Are you asking: Question' for ONE ADDITIONAL QUESTION that, if you knew its answer, would allow you to answer the student's question. Otherwise, if the attached context contains the definitions or information you need to answer the student question, in no more than three paragraphs answer the user's question; you may give longer answers if needed to fully construct a requested numerical example. Be VERY CAREFUL TO MATCH THE TERMINOLOGY AND DEFINITIONS, implicit or explicit, in the attached context, AND USE ONLY THEM. You may try to derive more creative examples ONLY if the user asks for a numerical example of some type when you can construct it precisely USING THE CONCEPTS, DEFINITIONS, AND TERMINOLOGY IN THE ATTACHED CONTEXT with high certainty, or when you are asked for an empirical example or an application of an idea IN THE ATTACHED CONTEXT applied to a new context, and you can construct one using the EXACT terminology and definitions in the text; remember, you are a precise TA who wants the student to understand but also wants to make sure you do not contradict the readings and lectures the student has been given in class. Please answer in the language of the student's question. Do not restate the question, do not apologize, do not refer to the context where you learned the answer, do not say you are an AI."
            send_to_gpt.append({"role": "system", "content": instructions})
            send_to_gpt.append({"role": "user", "content": original_question + "Attached context: " + most_similar})
            response = openai.ChatCompletion.create(
                messages=send_to_gpt,
                temperature=0.2,
                model = "gpt-4"
            )
        query = request.form['content1']
        tokens_sent = response["usage"]["prompt_tokens"]
        tokens_sent2 = response["usage"]["completion_tokens"]
        elapsed_time = time.time() - start_time  # calculate the elapsed time
        print(f"GPT4 Response gathered with proper html. You used {tokens_sent} prompt and {tokens_sent2} completion tokens. Time taken: {elapsed_time:.2f} seconds")
        reply = response["choices"][0]["message"]["content"].replace('\n', '<p>') + title_str
        return reply
    else:
        # Start background thread to load data when page first loads, even if user hasn't asked a question yet
        print("start thread to load data")
        thread = threading.Thread(target=background_loading)
        thread.start()
        # Render html while the data loads
        return render_template('index.html', assistant_name=assistant_name, instruct=instruct)
