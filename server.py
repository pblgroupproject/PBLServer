from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
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
        return jsonify({"error": "No image part"}), 400
    file = request.files['image']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        # Save the file with the constant name 'uploaded_image.jpg'
        extension = file.filename.rsplit('.', 1)[1].lower()
        saved_filename = f"{fixed_filename}.{extension}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))
        return jsonify({"message": "File uploaded successfully", "filename": saved_filename}), 200
    else:
        return jsonify({"error": "File type not permitted"}), 400


if __name__ == '__main__':
    # Run the application on host '0.0.0.0' and port 81
    app.run(host='0.0.0.0', port=81)
