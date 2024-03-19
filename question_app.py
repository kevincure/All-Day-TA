# This creates a student AI-based Question and Answer generator for your class
# Once you have your AI up and running, CreateQuestionBank lets you generate as many questions as you want, automatically, from your documents
# This frontend allows the students to access the questions.  
# Since the AI also generated explanations of the correct and incorrect answers, and common mistakes, these are shown to the student
# For best use cases on question generation, see the Readme.md

from flask import Flask, render_template, jsonify, request
import csv
import os

app = Flask(__name__)

question_folder = "Question Bank"
question_file = os.path.join(question_folder, "questionbank.csv")

def read_settings(file_name):
    settings = {}
    with open(file_name, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            settings[key] = value
    return settings
settings = read_settings("settings.txt")
classname = settings["classname"]

# Route to serve the HTML page
@app.route('/')
def index():
    return render_template('index_question.html', classname=classname)

# Route to get unique values for dropdown
@app.route('/get_unique_values')
def get_unique_values():
    unique_values = set()
    with open(question_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row:  # Ensure the row is not empty
                unique_values.add(row[0])
    return jsonify(list(unique_values))

# Route to get data based on selection
@app.route('/get_data')
def get_data():
    selected_value = request.args.get('selected_value')
    data = []
    with open(question_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            # we cam put a 0 at the start of the "topic" category when we want to ignore that question
            # this is a simple method to allow the professor to leave some questions out temporarily
            if row[0][0] == "0":  # Skip rows where the first character of the first column is "0"
                continue
            if row and row[0] == selected_value:
                # Structure the row data
                row_data = {
                    'title': row[2],  # Third column as 'title'
                    'responses': row[3:7],  # Fourth to seventh columns as 'responses'
                    'secret': row[7:11]
                }
                data.append(row_data)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)