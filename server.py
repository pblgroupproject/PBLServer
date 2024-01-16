from flask import Flask, render_template,jsonify,request 
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os



app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = './uploads'
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
    return render_template('index.html')

@app.route('/flutter',methods=['GET'])
def flutterReturn():
    json = {}
    inputargs = str(request.args['query'])
    json["output"] = inputargs
    return jsonify(json)

@app.route('/flutter/upload', methods = ["POST"])
def upload_file():
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
    file = request.files['image']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return jsonify({"error": "File type not permitted"}), 400


    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
