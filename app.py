# Flask app for All Day TA
# See readme.md for files that must be run before you use this
# PLEASE NOTE USAGE CAPS by tier on OpenAI, your students may hit these caps if you are not, say, Tier 4.  I prepay
#  at start of term to avoid this.
# Feb 19 2024 version

import numpy as np
import openai
import pandas as pd
import json
from flask import Flask, render_template, request, url_for, flash, session, redirect, jsonify, current_app
import requests
import os
import time
import threading
import cohere

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

# def load_data_to_app():
#     # Simulate long-loading data
#     print("Begin loading data")
#     df_chunks = pd.read_csv("textchunks-originaltext.csv")  # Example loading
#     embedding = np.load("textchunks.npy")  # Example loading
#     print("Data loaded")
#     return df_chunks, embedding
#
# # Function to run in background thread
# def background_loading():
#     print("background loading active")
#     app.df_chunks, app.embedding = load_data_to_app()
#
# # Start background thread outside any request context
# def start_background_loader():
#     print("background loader called")
#     thread = threading.Thread(target=background_loading)
#     thread.start()
#     return thread

# Function to load data
def load_data_to_app():
    print("Begin loading data")
    df_chunks = pd.read_csv("textchunks-originaltext.csv")  # Example loading
    embedding = np.load("textchunks.npy")  # Example loading
    print("Data loaded")
    return df_chunks, embedding

@app.before_first_request
def initialize_data():
    print("Loading data before first request...")
    app.df_chunks, app.embedding = load_data_to_app()

# handle POST when users enters query
@app.route('/', methods=('GET', 'POST'))

def index():
    if request.method == 'POST':
        # Load the text and its embeddings
        print("Starting to answer new question...")
        start_time = time.time()  # record the start time
        # Check if data is loaded, with a 1 second delay if not
        while not hasattr(current_app, 'df_chunks') or not hasattr(current_app, 'embedding'):
            print("Data not loaded yet, waiting...")
            time.sleep(1)  # Wait for 1 second before checking again
        # Access preloaded data
        df_chunks = current_app.df_chunks
        embedding = current_app.embedding
        timecheck(start_time, "Data loaded")
        # this is the question passed from the user query
        original_question = request.form['content1']
        prior_q_and_response = request.form['content2']

        # if answer to Q&A, don't embed a new search, just use existing context
        if original_question.startswith('a:'):
            print("Let's check the student's answer")
            # get the 'saved' information used to construct the last question
            # this comes from a cookie we save
            last_session = session.get('last_session', None)
            print("Ok, we have prior content via a cookie")
            if last_session is None:
                print("I don't know any old content")
                last_session = ""
            most_similar = last_session
            title_str = "<p></p>"
            print("Query being used: " + original_question)
            print("The content we draw on is " + most_similar)
            timecheck(start_time, "Original context for question loaded")
        # if anything other than answering a multiple choice question, go here
        else:
            # First see if there's any definition or technical question that will help us answer
            # This is very useful at avoiding hallucination on acronyms or other terms you use in your class
            additional_context=""
            content_definitions = f"Students are asking {original_question}. Are there any unclear acronyms or phrases you need to answer this question which may depend specifically on details of this course? Answer 'No.' or, if yes, return a very short question asking for the meaning of that acronym or definition you think is most likely to have a precise unique meaning in this class that could be easily confused. Say nothing else."
            response_definitions = query_openai(content_definitions, 25, "gpt-4", 0.0)
            print("Definitions needed? " + response_definitions)
            # if we need a definition, find the reranked single most similar chunk of text and include that as well
            if response_definitions != "No.":
                definition_q_embed = embed(response_definitions)
                similarities = compute_similarity(embedding, definition_q_embed)
                top_100_indices = np.argsort(similarities)[-100:][::-1]
                top_100_texts = df_chunks.iloc[top_100_indices]['Raw Text']
                rerank_definition_df = rerank(response_definitions, top_100_texts)
                most_similar_chunk_text = rerank_definition_df.iloc[0]['Text']
                additional_context += rerank_definition_df.iloc[0]['Text'] + " "
            timecheck(start_time, "Needed definitions acquired, if any")

            # Now let's check whether question is about the syllabus
            # In a sample of syllabus-related questions using GPT-4 and GPT-4-1106-preview ("Turbo"), GPT-4 correctly identified
            #    syllabus questions 91% of the time, and Turbo did 45% of the time, hence we use it here despite the expense
            #    Note that the system will likely answer correctly either way; this question just checks the student question then
            #    pushes the system to look for the answer in the syllabus file, a common request
            content = f"Students in {classname} taught by {professor} are asking questions. Class description: {classdescription} Is this question likely about the logistical details, schedule, nature, teachers, assignments, or syllabus of the course? Answer Yes or No and nothing else: {request.form['content1']}"
            response_syllabus = query_openai(content, 1, "gpt-4", 0.0)
            print("Is this a syllabus question? GPT-4 says " + response_syllabus)
            timecheck(start_time, "Checked whether this is a syllabus question")
            if response_syllabus.startswith('Y') or response_syllabus.startswith('y'):
            # Concatenate the strings to form the original_question value
                print("It seems like this question is about the syllabus")
                original_question = "I may be asking about a detail on the syllabus for " + classname + ". " + original_question

            # Now let's see if it might be a followup question
            # GPT-4 Turbo as of Dec 2023 way overidentifies these, while GPT-4 misses a few legitimate follow-ups
            if len(prior_q_and_response) > 1:
                content_followup = f"Consider this new user question: {original_question}. Their prior question and response was {prior_q_and_response} Would it be helpful to have the context of the previous question and response to answer the new one?  For example, the new question may refer to 'this' or 'that' or 'the company' or 'their' or 'his' or 'her' or 'the paper' or similar terms whose context is not clear if you only know the current question and don't see the previous question and response, or it may ask for more details or to summarize or rewrite or expand on the prior answer in a way that is impossible to do unless you can see the previous answer, or the user may just have said 'Yes' following up on a clarification in the previous question and answer.  Answer either Yes or No."
                response_followup = query_openai(content_followup, 1, "gpt-4", 0.0)
                print("Might this be a follow-up? GPT-4 says " + response_followup)
                timecheck(start_time, "Checked whether this is a followup")
                # Construct new prompt if AI says that this is a followup
                if response_followup.startswith('Y') or response_followup.startswith('y'):
                    # Update original_question to include prior 1
                    content_modify_followup = f"Consider this new user question: {original_question}. Their prior question and response was {prior_q_and_response} Rewrite the user's new question so that it is self-contained, including any background or related info from the prior question needed to answer it. Restrict the rewritten question to less than 3 sentences, at the very most."
                    original_question = query_openai(content_modify_followup, 100, "gpt-4", 0.0)
                    
            # Embed 'original_question', the user query modified to handle syllabus Qs and followups
            query_embed = embed(original_question)
            print("Query we embed is: " + original_question)

            # compute dot_product similarity for each row and add to new column
            df_chunks['similarity'] = compute_similarity(embedding, query_embed)
            # sort by similarity in descending order
            df_chunks = df_chunks.sort_values(by='similarity', ascending=False)
            # construct reranking
            rerank_df = rerank(original_question, df_chunks.head(100)['Raw Text'])
            # Select the most similar chunks
            most_similar_rerank_df = rerank_df.head(4)
            # if the extra block we got from the definition is repeated, drop it
            if additional_context in most_similar_rerank_df.iloc[:, 1].values:
                print("Extra definition matched, so we avoid repeating to save money")
                additional_context = ""
            if additional_context != "":
                print("Dropping one data chunk because we have the definition context as well")
                most_similar_rerank_df = most_similar_rerank_df.head(3)
            timecheck(start_time, "Query similarity sorted and reranked")

            most_similar_rerank = '\n\n'.join(row[1] for row in most_similar_rerank_df.values)

            # Count the number of occurrences of each title in most_similar_df
            title_counts = most_similar_rerank_df['Title'].value_counts()
            # Create a new dataframe with title and count columns, sorted by count in descending order
            title_df = pd.DataFrame({'Title': title_counts.index, 'Count': title_counts.values}).sort_values('Count', ascending=False)
            # Filter the titles that appear at least three times
            title_df_filtered = title_df[title_df['Count'] >= 2]
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

        # Now that we have the retrieval augmentation done, let's do the "generation" of the RAG
        # Note how good GPT4 is at not answering on unrelated tasks - it will answer "I don't know" given instructions if you ask it for a joke about fungi, or "what is your system prompt", or similar unrelated questions
        # Prior versions of this TA used followup ensemble questions to try to stop hallucination but it is largely not necessary anymore
        instructions = "You are a very truthful, precise TA in a " + classname + ", a " + classdescription + ".  You think step by step. A strong graduate student is asking you questions.  The answer to their query may appear in the following content drawn from class-related book chapters, handouts, transcripts, and articles. You CAN ONLY USE DEFINITIONS, ACRONYM DEFINITIONS, CONCEPTS, IDEAS FROM THE ATTACHED CONTEXT.  If you cannot answer the question under those constraints, and the question is DEFINITELY unrelated to class subject, syllabus, or course details, say 'I don't know - this appears unrelated to the class. Can you restate your question?' If the question is potentially related to the class, syllabus, or course details but the attached context does not give you enough to answer, say 'I don't know. Are you asking: Question' for ONE ADDITIONAL QUESTION that, if you knew its answer, would allow you to answer the student's question. Otherwise, if the attached context contains the definitions or information you need to answer the student question, in no more than three paragraphs answer the user's question; you may give longer answers if needed to fully construct a requested numerical example. Be VERY CAREFUL TO MATCH THE TERMINOLOGY AND DEFINITIONS, implicit or explicit, in the attached context, AND USE ONLY THEM. You may try to derive more creative examples ONLY if the user asks for a numerical example of some type when you can construct it precisely USING THE CONCEPTS, DEFINITIONS, AND TERMINOLOGY IN THE ATTACHED CONTEXT with high certainty, or when you are asked for an empirical example or an application of an idea IN THE ATTACHED CONTEXT applied to a new context, and you can construct one using the EXACT terminology and definitions in the text; remember, you are a precise TA who wants the student to understand but also wants to make sure you do not contradict the readings and lectures the student has been given in class. Please answer in the language of the student's question. Do not restate the question, do not apologize, do not refer to the context where you learned the answer, do not say you are an AI."
        content = original_question + "Attached context: " + most_similar_rerank + additional_context
        response_question = query_openai(content, 1000, "gpt-4", 0.2, instructions)
        timecheck(start_time, "LLM response acquired and html encoded")
        reply = response_question.replace('\n', '<p>') + title_str
        return reply
    else:
        return render_template('index.html', assistant_name=assistant_name, instruct=instruct)

# for debug
if __name__ == "__main__":
    app.run(debug=True)
