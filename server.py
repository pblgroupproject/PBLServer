from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from ultralytics import YOLO
from PIL import Image
import base64
from io import BytesIO
import json
import requests
from datetime import datetime



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



@app.route('/')
def server():
    return render_template('index.html', filename='uploaded_image.png')


@app.route('/keep-alive')
def keep_alive():
    return 'Server is alive'


@app.route('/flutter/upload', methods=["POST"])
def upload_file():
    user_id = request.args.get('user_id', default=None)

    if not user_id:
        return jsonify({'error': 'User id not provided'})
        
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
    file = request.files['image']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        saved_filename = f"{user_id}.png"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))
        return jsonify({"message": "File uploaded successfully", "filename": saved_filename}), 200
    else:
        return jsonify({"error": "File type not permitted"}), 400

def add_user_image(user_id, image_data, stage):
    try:
        conn = sqlite3.connect('data/user_images.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user_images (user_id, image_data, upload_time, stage)
            VALUES (?, ?, ?, ?)
        """, (user_id, image_data, datetime.now(), stage))

        conn.commit()

        conn.close()

        return True, None 

    except Exception as e:
        return False, str(e)

@app.route('/flutter/predict')
def predict():
    user_id = request.args.get('user_id', default=None)

    if not user_id:
        return jsonify({'error':'user id not provided'})


    filename = f"{user_id}.png"

    # Ensure the file exists
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({"error": f"File not found: {filename}"}), 404

    try:
        model = YOLO('version3_nanoyolo_best.pt')
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
        
        add_user_image(user_id, image_data, stage)

        return jsonify({"stage": f"{stage}", "file": image_data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

from flask import jsonify

@app.route('/api/images/<string:user_id>', methods=['GET'])
def get_user_images(user_id):
    try:
        conn = sqlite3.connect('data/user_images.db')
        cursor = conn.cursor()

        cursor.execute("SELECT image_data, upload_time, stage FROM user_images WHERE user_id = ? ORDER BY upload_time DESC", (user_id,))
        images = cursor.fetchall()

        conn.close()

        image_list = [{"image_data": image[0], "upload_time": image[1], "stage": image[2]} for image in images]

        return jsonify({"images": image_list}), 200

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

def botResponse(prompt):
    url = "https://api.worqhat.com/api/ai/content/v2"
    payload = {
        "conversation_history": [{
                                     "What services does Scalp Smart offer?": "Scalp Smart provides professional analysis of your hairfall stage and offers remedial oil, shampoo and hair mask products tailored to your needs."},
                                 {
                                     "How does Scalp Smart analyze my hairfall stage?": "We use advanced technology to examine your scalp condition and determine the stage of hairfall you are experiencing."},
                                 {
                                     "Can I get my scalp analyzed without visiting a clinic?": "Yes, you can use our convenient mobile app for a detailed analysis from the comfort of your home."},
                                 {
                                     "What are the different stages of hairfall that Scalp Smart identifies?": "We categorize hairfall into Normal, Stage 1, Stage 2, Stage 3, and Bald."},
                                 {
                                     "Are Scalp Smart products effective?": "Our products are specially formulated based on your hairfall stage and are designed to be effective in promoting scalp health."},
                                 {
                                     "Do I need a prescription for Scalp Smart products?": "No, our products are available for purchase directly without the need for a prescription."},
                                 {
                                     "How do I order Scalp Smart products?": "You can order our products through our website or mobile app."},
                                 {
                                     "What makes Scalp Smart different from other haircare companies?": "We provide personalized solutions by analyzing your hairfall stage and offering products tailored to your specific needs."},
                                 {
                                     "Is there a money-back guarantee for Scalp Smart products?": "Yes, we offer a satisfaction guarantee. If you're not satisfied with the results, we provide a refund."},
                                 {
                                     "Does Scalp Smart have a clinic for in-person consultations?": "No, we don't have a clinic. However, we can connect you with highly qualified doctors for professional advice."},
                                 {
                                     "How do I find a doctor recommended by Scalp Smart?": "We can provide you with a list of highly qualified doctors along with their qualifications, ratings, and clinic locations."},
                                 {
                                     "Can Scalp Smart cure baldness?": "While we can't guarantee a cure, our products are designed to improve scalp health and reduce hairfall."},
                                 {
                                     "Are Scalp Smart products suitable for all hair types?": "Yes, our products are formulated to cater to various hair types and conditions."},
                                 {
                                     "Can I use Scalp Smart products if I'm pregnant?": "This advice is specific to males. We recommend consulting with a healthcare professional before using our products, especially for pregnant individuals. For females, we recommend consulting with a healthcare professional, especially during pregnancy."},
                                 {
                                     "How often should I use Scalp Smart products?": "The usage frequency depends on your hairfall stage. Our product labels provide detailed instructions."},
                                 {
                                     "Is Scalp Smart affiliated with any hair clinics?": "We work independently, but we can connect you with qualified doctors for further consultation."},
                                 {
                                     "Can Scalp Smart help with dandruff issues?": "Yes, our products address various scalp issues, including dandruff."},
                                 {
                                     "Are there any side effects to using Scalp Smart products?": "Our products are formulated to minimize side effects, but it's essential to follow the usage instructions."},
                                 {
                                     "Can I get a discount on Scalp Smart products?": "We occasionally run promotions and discounts. Keep an eye on our website for the latest offers."},
                                 {
                                     "How long does it take to see results with Scalp Smart products?": "Results vary, but consistent use as per the instructions should show improvement over time."},
                                 {
                                     "Can I use Scalp Smart products on color-treated hair?": "Yes, our products are generally safe for use on color-treated hair. Check the product labels for any specific instructions."},
                                 {
                                     "Is Scalp Smart available internationally?": "Yes, we ship our products internationally. Shipping details are available on our website."},
                                 {
                                     "Can Scalp Smart products be used on children?": "We recommend consulting with a pediatrician before using our products on children."},
                                 {
                                     "How accurate is the hairfall analysis done by Scalp Smart?": "Our analysis is based on advanced technology and is generally accurate. However, for personalized advice, consulting with a doctor is recommended."},
                                 {
                                     "What information do I need to provide for the scalp analysis?": "The analysis typically requires clear pictures of your scalp, which can be submitted through our mobile app."},
                                 {
                                     "Can I consult with a doctor through the Scalp Smart app?": "Yes, we offer direct consultations through our app, connecting you with qualified doctors for personalized assistance."},
                                 {
                                     "Are there any dietary recommendations for addressing hairfall?": "We recommend maintaining a balanced diet for overall hair health. Consult with a doctor for personalized dietary advice."},
                                 {
                                     "How do I track my progress using Scalp Smart products?": "You can monitor changes in your hairfall stage over time. Regularly updating your profile on our app can help track progress."},
                                 {
                                     "Can I use Scalp Smart products along with other haircare products?": "It's generally recommended to use our products exclusively for the best results. Consult with a doctor if you plan to combine them with other products."},
                                 {
                                     "Does Scalp Smart have a loyalty program?": "As of now, we don't have a loyalty program set up."},
                                 {
                                     "I am at stage 2, how can I grow my hair back?": "To promote hair regrowth at Stage 2, we recommend consistent use of our products designed for that stage. Follow the usage instructions, and you may also consider consulting with a doctor for personalized advice."},
                                 {
                                     "Your model shows I am at stage 3, but I think I am at stage 1. Can the analysis be wrong?": "We understand discrepancies can occur. Please provide additional details or consider retaking the analysis for a more accurate result. If you believe you're at Stage 1, consult with a doctor for a professional assessment."},
                                 {
                                     "I have been using your products for the past 1 month but see no change, what should I do?": "While individual results may vary, it's common not to see significant changes within the first month. Hair regrowth is a gradual process. Keep using the products as directed, and if concerns persist, consult with a doctor for personalized guidance."},
                                 {
                                     "Can you provide more details on the recommended remedial oil for my hairfall stage?": "Our remedial oil is formulated based on your hairfall stage, containing ingredients to address specific concerns. You can find detailed information on the product label or our website."},
                                 {
                                     "How long does it usually take to see results from Scalp Smart products?": "The time it takes to see results can vary. Consistent use of our products, following the recommended instructions, is crucial. Visible improvements may take several weeks to months."},
                                 {
                                     " Are there any lifestyle changes I should consider to improve my hair health?": "Maintaining a healthy lifestyle can complement the effects of Scalp Smart products. Ensure a balanced diet, stay hydrated, and manage stress for overall hair health."},
                                 {
                                     " What is the recommended frequency of using the remedial oil for my stage of hairfall?": "The recommended frequency of using the remedial oil depends on your hairfall stage. Check the product label for specific instructions tailored to your needs."},
                                 {
                                     "Can I combine Scalp Smart products with other haircare treatments?": "While Scalp Smart products are designed to be effective on their own, consulting with a doctor before combining them with other treatments is advisable for personalized advice."},
                                 {
                                     "Is it possible to regress to a lower hairfall stage with proper treatment?": "Regression to a lower hairfall stage is possible with proper treatment and care. Consistent use of the recommended products is key to seeing positive changes."},
                                 {
                                     "How do I accurately take pictures of my scalp for the analysis?": "To take accurate pictures for the analysis, ensure good lighting and capture different angles of your scalp. Follow the instructions on the app for the best results."},
                                 {
                                     "Are there any specific diet recommendations to complement the use of Scalp Smart products?": "While our products support overall hair health, consulting with a doctor for personalized dietary recommendations is advisable for the best results."},
                                 {
                                     "Can stress or hormonal changes affect the effectiveness of Scalp Smart products?": "Stress and hormonal changes can influence hair health. While Scalp Smart products aim to address these issues, individual responses may vary. Consult with a doctor for personalized advice."},
                                 {
                                     "What are the potential side effects of using the remedial oil and shampoo?": "The potential side effects of the remedial oil and shampoo are minimal. However, if you experience any adverse reactions, discontinue use and consult with a doctor."},
                                 {
                                     "Can I use Scalp Smart products if I have a pre-existing scalp condition?": "Scalp Smart products are generally safe for use with pre-existing scalp conditions. However, consulting with a doctor before starting is recommended for personalized advice."},
                                 {
                                     "Is it normal to experience increased hair shedding initially when using the products?": "It's normal to experience increased hair shedding initially as old hairs are replaced by new ones. This phase typically subsides, leading to improved hair health."},
                                 {
                                     "Are there any specific tips for maintaining scalp health between product applications?": "Between product applications, maintain scalp health by keeping it clean and avoiding excessive heat styling. Follow any additional recommendations provided by your doctor."},
                                 {
                                     "How often should I update my profile on the app for accurate tracking of progress?": "Regularly updating your profile on the app with accurate information helps in tracking progress effectively. This ensures tailored recommendations based on your current status."},
                                 {
                                     "Can I use the remedial oil as an overnight treatment, or is it recommended for daytime use only?": "The remedial oil can be used as an overnight treatment or during the day. Follow the product label for specific instructions based on your hairfall stage."},
                                 {
                                     "Are there any restrictions on activities or products while using Scalp Smart products?": "While there are no strict restrictions, avoiding harsh chemicals or excessive heat on the scalp is advisable for the best results with Scalp Smart products."},
                                 {
                                     "Can I use the products on colored or chemically treated hair?": "Yes, Scalp Smart products can be used on colored or chemically treated hair. Check the product label for any specific instructions related to color-treated hair."},
                                 {
                                     "What is the recommended age range for using Scalp Smart products?": "Scalp Smart products are suitable for adults of all ages. However, consulting with a doctor before starting is recommended for personalized advice."},
                                 {
                                     "How can I differentiate between normal hair shedding and excessive hairfall?": "Normal hair shedding and excessive hairfall can be differentiated by considering factors like the amount of hair lost and changes in scalp health. Consult with a doctor for clarification."},
                                 {
                                     "Can Scalp Smart products be used in conjunction with prescription medications?": "Using Scalp Smart products in conjunction with prescription medications should be discussed with a doctor for personalized advice."},
                                 {
                                     "Do I need to continue using Scalp Smart products even after seeing improvement?": "While improvement may occur, continuing to use Scalp Smart products helps maintain results and supports ongoing scalp health."},
                                 {
                                     "Can the analysis be affected by factors like climate or seasonal changes?": "The analysis is designed to account for factors like climate or seasonal changes. However, individual responses may vary. Consistent product use is essential."},
                                 {
                                     "Are there any specific instructions for using the shampoo in combination with the remedial oil?": "There are no specific instructions for using the shampoo in combination with the remedial oil. Follow the usage guidelines on the product labels for the best results."},
                                 {
                                     "Is it advisable to consult with a doctor before starting Scalp Smart products?": "It is advisable to consult with a doctor before starting Scalp Smart products, especially if you have specific concerns or underlying health conditions."},
                                 {
                                     "What steps should I take if I experience an adverse reaction to the products?": "If you experience an adverse reaction, discontinue use of the products and consult with a doctor for guidance on the next steps."},
                                 {
                                     "Can I use Scalp Smart products on facial hair, such as a beard?": "Scalp Smart products are primarily formulated for scalp use. If you have specific concerns about facial hair, consult with a doctor for personalized advice."},
                                 {
                                     "How do I access the direct consultation feature with a doctor through the app?": "To access the direct consultation feature with a doctor through our app, follow these steps: Open the Scalp Smart app on your mobile device, navigate to the Consultation or Talk to a Doctor section, choose your preferred time slot or check for on-demand consultations, complete required information, confirm your appointment, and connect with a qualified doctor via video call or chat at the scheduled time."}],
        "preserve_history": True,
        "question": f"{prompt}",
        "randomness": 0.5,
        "response_type": "text",
        "stream_data": False,
        "training_data": "You are an official chatbot of Scalp Smart which is an AI powered platform to detect stage of hairloss."
    }
    headers = {
        "Authorization": "Bearer sk-eb55729f179343278d893701438e48dc",
        "Content-Type": "application/json"
    }
    response = requests.request("POST", url, json=payload, headers=headers)
    loc = response.text.find("content")
    return response.text[loc+10:-2]


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
