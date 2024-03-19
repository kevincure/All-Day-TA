# This allows you to approve/disable questions for you class Question Bank
# Once you have your AI up and running, CreateQuestionBank lets you generate as many questions as you want, automatically, from your documents
# The editor will let you see all questions that are neither approved nor disabled
# On the student-side, they will be able to see anything you haven't actively disabled, but this setup makes sure you only see "new" ones to disable
# Just as with the student question bank you can see the correct answer and explanations by clicking

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
    return render_template('index_edit_questions.html', classname=classname)

# Route to get unique values for dropdown
@app.route('/get_unique_values')
def get_unique_values():
    unique_values = set()
    with open(question_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row:  # Ensure the row is not empty
                # Skip rows where the first column starts with "0 "
                if row[0].startswith("0 "):
                    continue
                # If row starts with "00 ", ignore the "00 " part but count the remaining part
                elif row[0].startswith("00 "):
                    unique_value = row[0][3:]  # Exclude the first 3 characters ("00 ")
                    unique_values.add(unique_value)
                else:
                    unique_values.add(row[0])
    return jsonify(list(unique_values))

# Route to get data based on selection
@app.route('/get_data')
def get_data():
    selected_value = request.args.get('selected_value')
    data = []
    with open(question_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for original_index, row in enumerate(reader):
            if row[0].startswith("0 "):  # Skip disabled rows
                continue
            if row and row[0] == selected_value:
                row_data = {
                    'original_index': original_index,  # Include the original index
                    'title': row[2],
                    'responses': row[3:7],
                    'secret': row[7:11]
                }
                data.append(row_data)
    return jsonify(data)

@app.route('/disable_row', methods=['POST'])
def disable_row():
    try:
        # Extracting the original_index and converting it to an integer
        original_index = int(request.json.get('original_index'))  # Convert to int

        # Now ensure the file reading and row updating logic uses this `original_index`
        with open(question_file, 'r', encoding='utf-8') as file:
            rows = list(csv.reader(file))

        if 0 <= original_index < len(rows):  # Correctly compare integer values
            # Prepend "0 " to the first column of the specified row
            rows[original_index][0] = "0 " + rows[original_index][0]

            # Write the updated data back to the CSV
            with open(question_file, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(rows)
            return jsonify({'success': True, 'message': 'Row approved successfully.'})
        else:
            # Index is out of range
            return jsonify({'success': False, 'message': 'Invalid index'}), 400
    except ValueError as e:  # Catch conversion errors
        return jsonify({'success': False, 'message': 'Invalid index value'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
@app.route('/approve_row', methods=['POST'])
def approve_row():
    try:
        # Extracting the original_index and converting it to an integer
        original_index = int(request.json.get('original_index'))  # Convert to int

        # Now ensure the file reading and row updating logic uses this `original_index`
        with open(question_file, 'r', encoding='utf-8') as file:
            rows = list(csv.reader(file))

        if 0 <= original_index < len(rows):  # Correctly compare integer values
            # Prepend "00 " to the first column of the specified row
            rows[original_index][0] = "00 " + rows[original_index][0]

            # Write the updated data back to the CSV
            with open(question_file, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(rows)
            return jsonify({'success': True, 'message': 'Row approved successfully.'})
        else:
            # Index is out of range
            return jsonify({'success': False, 'message': 'Invalid index'}), 400
    except ValueError as e:  # Catch conversion errors
        return jsonify({'success': False, 'message': 'Invalid index value'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)