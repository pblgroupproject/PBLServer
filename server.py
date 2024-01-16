from flask import Flask, render_template,jsonify,request 
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os



app = Flask(__name__)
CORS(app)

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
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({"message": "File uploaded successfully"}), 200

    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
