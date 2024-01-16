from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config['UPLOAD_FOLDER'] = './uploads'
allowed_extensions = set(['png', 'jpg', 'jpeg', 'gif'])
fixed_filename = 'uploaded_image'


# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


# Create the uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/')
def server():
    # Render the index.html template
    return render_template('index.html')


@app.route('/flutter', methods=['GET'])
def flutter_return():
    # Get the 'query' parameter from the request and return it as JSON
    json = {}
    input_args = str(request.args['query'])
    json["output"] = input_args
    return jsonify(json)


@app.route('/flutter/upload', methods=["POST"])
def upload_file():
    if 'image' not in request.files:
        # Return an error if no 'image' part is found in the request
        return jsonify({"error": "No image part"}), 400
    file = request.files['image']

    if file.filename == '':
        # Return an error if no file is selected
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        # Save the uploaded file with a secure filename to the specified UPLOAD_FOLDER
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        # Return an error if the file type is not permitted
        return jsonify({"error": "File type not permitted"}), 400

if __name__ == '__main__':
    # Run the application on host '0.0.0.0' and port 81
    app.run(host='0.0.0.0', port=81)
