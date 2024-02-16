from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from ultralytics import YOLO
from PIL import Image
import base64
from io import BytesIO

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config['UPLOAD_FOLDER'] = './uploads'
app.config['RESULT_FOLDER'] = './Results'

allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}


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
    print("Hello")

    return render_template('index.html', filename='uploaded_image.png')


@app.route('/flutter', methods=['GET'])
def flutter_return():
    # Get the 'query' parameter from the request and return it as JSON
    json_data = {}
    input_args = str(request.args['query'])
    json_data["output"] = input_args
    return jsonify(json_data)


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


@app.route('/flutter/predict')
def predict():
    filename = "uploaded_image.png"  # or get the actual filename from the request

    # Ensure the file exists
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({"error": f"File not found: {filename}"}), 404

    try:
        model = YOLO('best.pt')
        results = model(file_path)
        result = results[0]
        box = result.boxes[0]
        class_id = int(box.cls[0].item())
        
        stage = "normal"
        if class_id == 0:
            stage = "bald"
        elif class_id == 1:
            stage = "normal"
        elif class_id == 2:
            stage = "stage 1"
        elif class_id == 3:
            stage = "stage 2"
        elif class_id == 4:
            stage = "stage 3"

        im_array = result.plot()
        result_image = Image.fromarray(im_array[..., ::-1])
        image_buffer = BytesIO()
        result_image.save(image_buffer, format="PNG")
        image_data = base64.b64encode(image_buffer.getvalue()).decode("utf-8")        

        return jsonify({"stage": f"{stage}", "file": image_data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/image/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/product/api/<int:product_id>')
def get_product(product_id):
    if not os.path.exists('data/database.db'):
        return jsonify({'error': 'Database not found'}), 500  

    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM products WHERE ID = ?', (product_id,))
    product = cursor.fetchone()

    conn.close()

    if product:
        keys = ['ID', 'NAME', 'PRICE', 'IMAGE', 'DESCRIPTION', 'BRAND', 'BENEFITS', 'URL', 'CATEGORY', 'BEST_SELLER']
        return jsonify(dict(zip(keys, product)))
    else:
        return jsonify({'error': 'Product not found'}), 404

@app.route('/product/api/')
def get_all_products():
    if not os.path.exists('data/database.db'):
        return jsonify({'error': 'Database not found'}), 500  

    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    conn.close()
    if products:
        keys = ['ID', 'NAME', 'PRICE', 'IMAGE', 'DESCRIPTION', 'BRAND', 'BENEFITS', 'URL', 'CATEGORY', 'BEST_SELLER']
        return jsonify([dict(zip(keys, product)) for product in products])
    else:
        return jsonify([])



if __name__ == '__main__':
    # Run the application on host '0.0.0.0' and port 81
    app.run(host='0.0.0.0', port=81)
