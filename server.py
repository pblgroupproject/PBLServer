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
chat_history = []

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


# Create the uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def botResponse(prompt):
    url = "https://api.worqhat.com/api/ai/content/v2"
    with open("chat_bot_dataset.json", "r") as json_file:
        data = json.load(json_file)
        payload = data["payload"]
        headers = data["headers"]

    response = requests.request("POST", url, json=payload, headers=headers)
    loc = response.text.find("content")
    return response.text[loc+10:-2]


@app.route('/')
def server():
    return render_template('index.html', filename='uploaded_image.png')


@app.route('/keep-alive')
def keep_alive():
    return 'Server is alive'


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

@app.route('/product/api/<int:product_id>', methods=['GET','PATCH','DELETE'])
def get_product(product_id):
    if not os.path.exists('data/database.db'):
        return jsonify({'error': 'Database not found'}), 500  
    if request.method == 'GET':
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
    elif request.method == 'DELETE':
        # Check if the product exists
        conn = sqlite3.connect('data/database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE ID = ?', (product_id,))
        existing_product = cursor.fetchone()
        if existing_product is None:
            conn.close()
            return jsonify({'error': 'Product not found'}), 404

        # Delete the product from the database
        cursor.execute('DELETE FROM products WHERE ID = ?', (product_id,))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Product deleted successfully'}), 200
    
    elif request.method == 'PATCH':
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Check if the product exists
        conn = sqlite3.connect('data/database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE ID = ?', (product_id,))
        existing_product = cursor.fetchone()
        conn.close()
        if existing_product is None:
            return jsonify({'error': 'Product not found'}), 404

        # Update the product fields if they are present in the request
        fields_to_update = ['NAME', 'PRICE', 'IMAGE', 'DESCRIPTION', 'BRAND', 'BENEFITS', 'URL', 'CATEGORY', 'BEST_SELLER']
        for field in fields_to_update:
            if field in data:
                conn = sqlite3.connect('data/database.db')
                cursor = conn.cursor()
                cursor.execute(f'UPDATE products SET {field} = ? WHERE ID = ?', (data[field], product_id))
                conn.commit()
                conn.close()

        return jsonify({'message': 'Product updated successfully'}), 200
    else:
        return jsonify({'error': 'Method not allowed'}), 405

@app.route('/flutter/chatbot/prompt', methods = ['POST'])
def chatbot():
    if request.method == 'POST':
        prompt = request.json['prompt']

        response = botResponse(prompt)

        return jsonify({'response': response})
    else:
        return jsonify({'error' : 'Only POST requests are allowed'})

@app.route('/product/api/', methods=['GET','POST'])
def get_all_products():
    if not os.path.exists('data/database.db'):
        return jsonify({'error': 'Database not found'}), 500  
    if request.method == 'GET':
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
            
    elif request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Check if all required fields are present
        required_fields = ['NAME', 'PRICE', 'IMAGE', 'DESCRIPTION', 'BRAND', 'BENEFITS', 'URL', 'CATEGORY', 'BEST_SELLER']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        # Extract data from request and insert into the database
        name = data.get('NAME')
        price = data.get('PRICE')
        image = data.get('IMAGE')
        description = data.get('DESCRIPTION')
        brand = data.get('BRAND')
        benefits = data.get('BENEFITS')
        url = data.get('URL')
        category = data.get('CATEGORY')
        best_seller = data.get('BEST_SELLER')

        # Insert the data into the database (this part is just a placeholder, you need to modify it based on your database setup)
        conn = sqlite3.connect('data/database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO products (NAME, PRICE, IMAGE, DESCRIPTION, BRAND, BENEFITS, URL, CATEGORY, BEST_SELLER) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (name, price, image, description, brand, benefits, url, category, best_seller))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Product added successfully'}), 201
    else:
        return jsonify({'error': 'Method not allowed'}), 405
        


if __name__ == '__main__':
    # Run the application on host '0.0.0.0' and port 81
    app.run(host='0.0.0.0', port=81)
