from flask import Flask, render_template, jsonify, request, send_from_directory

from roboflow import Roboflow

from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config['UPLOAD_FOLDER'] = './uploads'
app.config['RESULT_FOLDER'] = './Results'

allowed_extensions = set(['png', 'jpg', 'jpeg', 'gif'])


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
    return render_template('index.html', filename='uploaded_image.png')


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
        saved_filename = "uploaded_image.png"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))
        return jsonify({"message": "File uploaded successfully", "filename": saved_filename}), 200
    else:
        return jsonify({"error": "File type not permitted"}), 400


 # rf = Roboflow(api_key="M95kxAi98WPQph7csqI5")

@app.route('/flutter/predict')
def predict():
    filename = "uploaded_image.png"  # or get the actual filename from the request

    # Ensure the file exists
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({"error": f"File not found: {filename}"}), 404

    try:
        rf = Roboflow(api_key="M95kxAi98WPQph7csqI5")  # Use your actual API key
        project = rf.workspace().project("hairfalldetection")
        model = project.version(1).model

        # infer on a local image
        result_generated = model.predict(file_path).json()
        for prediction in result_generated['predictions']:
            print(prediction['class'])

        # save an image annotated with your predictions
        model.predict(file_path).save(os.path.join(app.config['RESULT_FOLDER'], filename))

        return jsonify(result_generated), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# @app.route('/image/<filename>')
# def serve_image(filename):
#     return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/image/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)





if __name__ == '__main__':
    # Run the application on host '0.0.0.0' and port 81
    app.run(host='0.0.0.0', port=81)
