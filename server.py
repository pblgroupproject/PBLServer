from flask import Flask, render_template,jsonify,request 
from flask_cors import CORS
import werkzeug
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
def upload():
        if(request.method == "POST"):
            imagefile = request.files['image']
            filename = werkzeug.utils.secure_filenae(imagefile.filename)
            imagefile.save("./uploadedimages/"+filename)
            return jsonify({
                "message" : "Image Uploaded Successfully"})

    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
