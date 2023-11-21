# Nov 2023, changes to use GPT4, drop "is this answer right?" due to costs
# Current cost average 3.84 cents per question/answer, vs. .33 cents with GPT3.5 only, but quality is definitely better
# Need to fix how we store "last_session"; as cookie, it only stores 3900 bytes instead of the full context when doing Q&A
# Need to fix how the "in the related context", "per the article" etc are referenced

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
# get settings
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
num_chunks = int(settings['num_chunks'])
# get API_key
with open("APIkey.txt", "r") as f:
    openai.api_key = f.read().strip()

# this lets us load the data only once and to do it in the background while the user types the first q
df_chunks = None
embedding = None
last_session = None
# this ensures we load the data before taking an input
load_lock = threading.Lock()
def load_df_chunks():
    global df_chunks, embedding
    # maybe just save this numpy embedding?
    if embedding is None:
        df_chunks = pd.read_csv(dataname+"-originaltext.csv")
        embedding = np.load(dataname+".npy")
    else:
        print("Database already loaded")
    return df_chunks
def background_loading():
    with load_lock:
        global df_chunks, embedding
        df_chunks = load_df_chunks()
        print("Loaded data from background")

def grab_last_response():
    global last_session
    last_session = session.get('last_session', None)
    print("Ok, we have last session")
    if last_session is None:
        print("I don't know old content")
        last_session = ""
    return last_session

    
@app.route('/', methods=('GET', 'POST'))

def index():
    if request.method == 'POST':
        with load_lock:
            # Load the text and its embeddings
            print("ok, starting")
            start_time = time.time()  # record the start time
            df_chunks = load_df_chunks() # get df_chunks from the global
            elapsed_time = time.time() - start_time  # calculate the elapsed time
            print(f"Data loaded. Time taken: {elapsed_time:.2f} seconds")
            original_question = request.form['content1']

            # if there is a previous question and it's not multiple choice or its answer, check to see if the new one is a syllabus q or followup
            # this works OK for now, it will work better with GPT4
            if not (request.form['content1'].startswith('m:') or request.form['content1'].startswith('M:') or request.form['content1'].startswith('a:')):
                # first let's see if it's on the syllabus
                send_to_gpt = []
                send_to_gpt.append({"role": "user",
                                    "content": f"Students in {classname} taught by {professor} is asking questions. Class description: {classdescription}  Is this question likely about the logistical details, schedule, nature, teachers, assignments, or syllabus of the course?  Answer Yes or No and nothing else: {request.form['content1']}"})
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    max_tokens=1,
                    temperature=0.0,
                    messages=send_to_gpt
                )
                print("Is this a syllabus question (new2)? GPT-4 says " + response["choices"][0]["message"]["content"])
                tokens_sent = response["usage"]["prompt_tokens"]
                tokens_sent2 = response["usage"]["completion_tokens"]
                elapsed_time = time.time() - start_time  # calculate the elapsed time
                print(f"GPT4 Response gathered. You used {tokens_sent} prompt and {tokens_sent2} completion tokens. Time taken: {elapsed_time:.2f} seconds")                # Construct new prompt if AI says that this is a syllabus question
                if response["choices"][0]["message"]["content"].startswith('Y') or response["choices"][0]["message"][
                    "content"].startswith('y'):
                    # Concatenate the strings to form the original_question value
                    print("It seems like this question is about the syllabus")
                    original_question = "I may be asking about a detail on the syllabus for " + classname + ". " + request.form['content1']
                else:
                    # if not on the syllabus, and it might be a followup, see if it is
                    if len(request.form['content2'])>1:
                        send_to_gpt = []
                        send_to_gpt.append({"role": "user",
                                            "content": f"Consider this new user question: {request.form['content1']}. Their prior question and response was {request.form['content2']} Would it be helpful to have the context of the previous question and response to answer the new one?  For example, the new question may refer to 'this' or 'that' or 'the company' or 'their' or 'his' or 'her' or 'the paper' or similar terms whose context is not clear if you only know the current question and don't see the previous question and response, or it may ask for more details or to summarize or rewrite or expand on the prior answer in a way that is impossible to do unless you can see the previous answer.  Answer either Yes or No."})
                        response = openai.ChatCompletion.create(
                            model="gpt-4-1106-preview",
                            max_tokens=1,
                            temperature=0.0,
                            messages=send_to_gpt
                        )
                        print(f"Consider this new question from a user: {request.form['content1']}. Their prior question and the response was {request.form['content2']} Think very logically.  Is the information requested in the new question potentially related to the previous question and response? Answer either Yes or No.")
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
                print("The content we draw on begins " + most_similar[:200])
                elapsed_time = time.time() - start_time  # calculate the elapsed time
                print(f"Original context for question loaded. Time taken: {elapsed_time:.2f} seconds")
            else:
                embedthequery = openai.Embedding.create(
                    model="text-embedding-ada-002",
                    input=original_question
                )
                print("Query we asked is: " + original_question)
                query_embed=embedthequery["data"][0]["embedding"]
                elapsed_time = time.time() - start_time  # calculate the elapsed time
                print(f"Query embedded. Time taken: {elapsed_time:.2f} seconds")

                # function to compute dot product similarity; tested using Faiss library and didn't really help
                def compute_similarity(embedding, userquery):
                   similarities = np.dot(embedding, userquery)
                   return similarities

                # compute similarity for each row and add to new column
                df_chunks['similarity'] = np.dot(embedding, query_embed)
                # sort by similarity in descending order
                df_chunks = df_chunks.sort_values(by='similarity', ascending=False)
                # Select the top query_similar_number most similar articles
                most_similar_df = df_chunks.head(num_chunks)
                elapsed_time = time.time() - start_time  # calculate the elapsed time
                print(f"Original query similarity sorted. Time taken: {elapsed_time:.2f} seconds")
                # Drop duplicate rows based on Title and Text columns
                most_similar_df = most_similar_df.drop_duplicates(subset=['Title', 'Text'])
                # Count the number of occurrences of each title in most_similar_df
                title_counts = most_similar_df['Title'].value_counts()
                # Create a new dataframe with title and count columns, sorted by count in descending order
                title_df = pd.DataFrame({'Title': title_counts.index, 'Count': title_counts.values}).sort_values('Count', ascending=False)
                # Filter the titles that appear at least three times
                title_df_filtered = title_df[title_df['Count'] >= 3]
                # Get the most common titles in title_df_filtered
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

            # I use very low temperature to give most "factual" answer
            reply = []
            print("The related content is: " + most_similar[:1000])
            send_to_gpt = []
            if request.form['content1'].startswith('m:'):
                instructions = "You are a very truthful, precise TA in a " + classname + ".  You think step by step. A strong graduate student is using you as a tutor.  The student would like you to prepare a challenging multiple choice question on the requested topic drawing ONLY on the attached context.  You do not have to merely ask about definitions, but can also construct scenarios or creative examples. NEVER refer to 'the attached context' or 'according to the article' or similar. Assume the student has no idea what context you are drawing your question from, and NEVER state the context you are drawing the question from: just state the question, then state options A to D. After the question, write <span style=\"display:none\"> then give your answer and a short explanation, then after your answer and explanation close the span with </span>"
                original_question = "Construct a challenging multiple-choice question to test me on a concept related to " + request.form['content1'][len('m:'):].strip()
                send_to_gpt.append({"role": "system", "content": instructions + most_similar})
                send_to_gpt.append({"role": "user", "content": original_question})
                response = openai.ChatCompletion.create(
                    messages=send_to_gpt,
                    temperature=0.2,
                    model = "gpt-4-1106-preview"
                )
                # save question content for response
                truncated_most_similar = most_similar[:3900]
                session['last_session'] = truncated_most_similar
                print("saving old context to session variable")
            elif request.form['content1'].startswith('a:'):
                instructions = "You are a very truthful, precise TA in a " + classname + ".  You think step by step. You are testing a strong graduate student on their knowledge.  The student would like you, using the attached context, to tell them whether they have answered the attached multiple choice question correctly.  Draw ONLY on the attached context for definitions and theoretical content.  Never refer to 'the attached context' or 'the article says that' or other context: just state your answer and the rationale."
                original_question =  request.form['content1'][len('a:'):].strip()
                send_to_gpt.append({"role": "system", "content": instructions + most_similar})
                send_to_gpt.append({"role": "user", "content": original_question})
                response = openai.ChatCompletion.create(
                    messages=send_to_gpt,
                    temperature=0.2,
                    model = "gpt-4-1106-preview"
                )
            else:
                instructions = "You are a very truthful, precise TA in a " + classname + ", a " + classdescription + ".  You think step by step. A strong graduate student is asking you questions.  The answer to their query may appear in the attached book chapters, handouts, transcripts, and articles.  If it does, in no more than three paragraphs answer the user's question; you may answer in longer form with more depth if you need it to fully construct a requested numerical example.  Do not restate the question, do not refer to the context where you learned the answer, do not say you are an AI; just answer the question.  Say 'I don't know' if you can't find the answer to the original question in the text below; be very careful to match the terminology and definitions, implicit or explicit, used in the attached context. You may try to derive more creative examples ONLY if the user asks for a numerical example of some type when you can construct it precisely using the terminology found in the attached context with high certainty, or when you are asked for an empirical example or an application of an idea to a new context, and you can construct one using the exact terminology and definitions in the text; remember, you are a precise TA who wants the student to understand but also wants to make sure you do not contradict the readings and lectures the student has been given in class. Please answer in the language of the student's question."
                send_to_gpt.append({"role": "system", "content": instructions + most_similar})
                send_to_gpt.append({"role": "user", "content": original_question})
                response = openai.ChatCompletion.create(
                    messages=send_to_gpt,
                    temperature=0.2,
                    model = "gpt-4-1106-preview"
                )
            query = request.form['content1']
            tokens_sent = response["usage"]["prompt_tokens"]
            tokens_sent2 = response["usage"]["completion_tokens"]
            elapsed_time = time.time() - start_time  # calculate the elapsed time
            print(f"GPT4 Response gathered. You used {tokens_sent} prompt and {tokens_sent2} completion tokens. Time taken: {elapsed_time:.2f} seconds")
            reply1 = response["choices"][0]["message"]["content"]

            # # check to make sure GPT is happy with the answer - commented out currently to save on cost
            # send_to_gpt = []
            # send_to_gpt.append({"role": "system", "content": "Just say 'Yes' or 'No'. Do not give any other answer."})
            # send_to_gpt.append({"role": "user",
            #                     "content": f"User: {original_question}  Attendant: {reply1} Was the Attendant completely unable to answer the user's question?"})
            # response = openai.ChatCompletion.create(
            #     model="gpt-4-1106-preview",
            #     max_tokens=1,
            #     temperature=0.0,
            #     messages=send_to_gpt
            # )
            # print("Did we fail to answer the question with " + reply1 + response["choices"][0]["message"]["content"])
            # tokens_sent = response["usage"]["prompt_tokens"]
            # tokens_sent2 = response["usage"]["completion_tokens"]
            # elapsed_time = time.time() - start_time  # calculate the elapsed time
            # print(
            #     f"GPT4 Turbo Response gathered. You used {tokens_sent} prompt and {tokens_sent2} completion tokens. Time taken: {elapsed_time:.2f} seconds")
            # # if you don't find the answer, grab the most article we think is most related and try to prompt a followup
            # if response["choices"][0]["message"]["content"].lower().startswith("y") and not request.form['content1'].startswith('a:'):
            #     send_to_gpt = []
            #     # need to reload df_chunks since its order no longer syncs with embeddings
            #     df_chunks = pd.read_csv(dataname + "-originaltext.csv")
            #     # get the article that was most related when we couldn't find the answer
            #     mostcommontitle = title_df["Title"].value_counts().index[0]
            #     title_counts = title_df["Title"].value_counts()
            #     # Check if there is more than one entry in title_df and the second most common title appears at least twice
            #     if len(title_counts) > 1 and title_counts.iloc[1] >= 2:
            #         secondmostcommontitle = title_counts.index[1]
            #         # now prompt again, giving that article as context
            #         followup_input = f'Using {mostcommontitle}: {original_question}'
            #         embedthequery2 = openai.Embedding.create(
            #             model="text-embedding-ada-002",
            #             input=followup_input
            #         )
            #         query_embed2 = embedthequery2["data"][0]["embedding"]
            #         followup_input2 = f'Using {secondmostcommontitle}: {original_question}'
            #         embedthequery3 = openai.Embedding.create(
            #             model="text-embedding-ada-002",
            #             input=followup_input
            #         )
            #         query_embed3 = embedthequery3["data"][0]["embedding"]
            #         # compute similarity for each row and add to new column
            #         df_chunks['similarity2'] = np.dot(embedding, query_embed2)
            #         df_chunks['similarity3'] = np.dot(embedding, query_embed3)
            #         # sort by similarity in descending order
            #         df_chunks = df_chunks.sort_values(by='similarity2', ascending=False)
            #         # Select the top query_similar_number most similar articles
            #         most_similar_df_fhead = df_chunks.head(5)
            #         print(df_chunks.head(2))
            #         # sort by similarity in descending order
            #         df_chunks = df_chunks.sort_values(by='similarity3', ascending=False)
            #         # Select the top query_similar_number most similar articles
            #         most_similar_df_fhead = pd.concat([most_similar_df_fhead, df_chunks.head(5)], axis=1)
            #         print(df_chunks.head(2))
            #         elapsed_time = time.time() - start_time  # calculate the elapsed time
            #         print(f"Followup queries similarity sorted. Time taken: {elapsed_time:.2f} seconds")
            #         # Drop duplicate rows based on Title and Text columns
            #         most_similar_df_follow = most_similar_df_fhead.drop_duplicates(subset=['Title', 'Text'])
            #         mostcommontitle = mostcommontitle + " and " + secondmostcommontitle
            #         most_similar_followup = "The best guess at related texts is/are " + mostcommontitle + '\n\n'.join(
            #             row[1] for row in most_similar_df_follow.values)
            #     else:
            #         # now prompt again, giving that article as context
            #         followup_input = f'Using {mostcommontitle}: {original_question}'
            #         embedthequery2 = openai.Embedding.create(
            #             model="text-embedding-ada-002",
            #             input=followup_input
            #         )
            #         query_embed2 = embedthequery2["data"][0]["embedding"]
            #         # compute similarity for each row and add to new column
            #         df_chunks['similarity2'] = np.dot(embedding, query_embed2)
            #         # sort by similarity in descending order
            #         df_chunks = df_chunks.sort_values(by='similarity2', ascending=False)
            #         # Select the top query_similar_number most similar articles
            #         most_similar_df_fhead = df_chunks.head(10)
            #         print(df_chunks.head(2))
            #         elapsed_time = time.time() - start_time  # calculate the elapsed time
            #         print(f"Followup query similarity sorted. Time taken: {elapsed_time:.2f} seconds")
            #         # Drop duplicate rows based on Title and Text columns
            #         most_similar_df_follow = most_similar_df_fhead.drop_duplicates(subset=['Title', 'Text'])
            #         most_similar_followup = "The best guess at related texts is/are " + mostcommontitle + '\n\n'.join(
            #             row[1] for row in most_similar_df_follow.values)
            #     # now prompt again, giving that article as context
            #     followup_input = f'Using {mostcommontitle}: {original_question}'
            #     send_to_gpt.append({"role": "system", "content": instructions + most_similar_followup})
            #     send_to_gpt.append({"role": "user", "content": f'Using {mostcommontitle}: {original_question}'})
            #     response = openai.ChatCompletion.create(
            #         model="gpt-3.5-turbo-0613",
            #         messages=send_to_gpt
            #     )
            #     tokens_sent = response["usage"]["prompt_tokens"]
            #     tokens_sent2 = response["usage"]["completion_tokens"]
            #     elapsed_time = time.time() - start_time  # calculate the elapsed time
            #     print(
            #         f"GPT35 Response gathered. You used {tokens_sent} prompt and {tokens_sent2} completion tokens. Time taken: {elapsed_time:.2f} seconds")
            #     reply1 = response["choices"][0]["message"]["content"]
            #     # check to see if follow-up was answered
            #     send_to_gpt = []
            #     send_to_gpt.append(
            #         {"role": "system", "content": "Just say 'Yes' or 'No'. Do not give any other answer."})
            #     send_to_gpt.append({"role": "user",
            #                         "content": f"User: {original_question}  Attendant: {reply1} Was the Attendant completely unable to answer the user's question?"})
            #     response = openai.ChatCompletion.create(
            #         model="gpt-4-1106-preview",
            #         max_tokens=1,
            #         temperature=0.0,
            #         messages=send_to_gpt
            #     )
            #     print("Did we fail to answer the followup question? " + response["choices"][0]["message"]["content"])
            #     if response["choices"][0]["message"]["content"].lower().startswith("y") and not request.form[
            #         'content1'].startswith('a:'):
            #         reply1 = "I'm sorry but I cannot answer that question.  Can you rephrase or ask an alternative?"
            #     tokens_sent = response["usage"]["prompt_tokens"]
            #     tokens_sent2 = response["usage"]["completion_tokens"]
            #     elapsed_time = time.time() - start_time  # calculate the elapsed time
            #     print(
            #         f"GPT4 Turbo Response gathered. You used {tokens_sent} prompt and {tokens_sent2} completion tokens. Time taken: {elapsed_time:.2f} seconds")

            reply1=reply1.replace('\n', '<p>')
            reply = reply1 + title_str
            return reply
    else:
        # Start background thread to load data
        thread = threading.Thread(target=background_loading)
        thread.start()
        # Render template with no data
        return render_template('index.html', assistant_name=assistant_name, instruct=instruct)
