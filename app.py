import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, static_folder='public')

# Configure Gemini API
api_key = os.environ.get('GEMINI_API_KEY', 'AIzaSyBNDr4rWhCFZoDGgVqN1l4YbtnVBHfUWNM')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-now')
def get_now():
    return render_template('contact.html')

@app.route('/ai')
def ai():
    return render_template('ai.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/motor-insurance')
def motor_insurance():
    return render_template('motor_insurance.html')

@app.route('/health-insurance')
def health_insurance():
    return render_template('health_insurance.html')

@app.route('/travel-insurance')
def travel_insurance():
    return render_template('travel_insurance.html')

@app.route('/marine-cargo-insurance')
def marine_cargo_insurance():
    return render_template('marine_cargo_insurance.html')

@app.route('/fire-burglary-insurance')
def fire_burglary_insurance():
    return render_template('fire_burglary_insurance.html')

@app.route('/workmen-compensation')
def workmen_compensation():
    return render_template('workmen_compensation.html')

@app.route('/shopkeeper-insurance')
def shopkeeper_insurance():
    return render_template('shopkeeper_insurance.html')

@app.route('/renewal')
def renewal():
    return render_template('renewal.html')

@app.route('/career')
def career():
    return render_template('career.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/blog/b1')
def blog_b1():
    return render_template('blog_b1.html')

@app.route('/blog/b2')
def blog_b2():
    return render_template('blog_b2.html')

@app.route('/blog/b3')
def blog_b3():
    return render_template('blog_b3.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')

    # Use Gemini API to generate response
    try:
        response = model.generate_content(user_message)
        response_text = response.text
    except Exception as e:
        response_text = f"Error generating response: {str(e)}"

    return jsonify({'response': response_text})

if __name__ == '__main__':
    app.run(debug=True)
