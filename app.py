import os
from dotenv import load_dotenv
from groq import Groq
from flask import Flask, render_template, request, jsonify, send_from_directory
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Load environment variables from .env file
load_dotenv()

# Flask will automatically handle serving files from the 'static' folder
# through the /static URL path.
app = Flask(__name__)


# Configure Groq API
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Email server configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "sparksolutionfreelancing@gmail.com"  # Replace with your Gmail address
SMTP_PASSWORD = "oqny rnem dbap yofq "      # Replace with your Gmail App Password

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

@app.route('/workmen-compensation-renewal')
def workmen_compensation_renewal():
    return render_template('workmen_compensation_renewal.html')

@app.route('/shopkeeper-insurance')
def shopkeeper_insurance():
    return render_template('shopkeeper_insurance.html')

@app.route('/miscellaneous')
def miscellaneous():
    return render_template('miscellaneous.html')

@app.route('/renewal')
def renewal():
    return render_template('renewal.html')

@app.route('/health-insurance-renewal')
def health_insurance_renewal():
    return render_template('health_insurance_renewal.html')

@app.route('/travel-insurance-renewal')
def travel_insurance_renewal():
    return render_template('travel_insurance_renewal.html')

# New form routes
@app.route('/marine-form')
def marine_form():
    return render_template('marine_form.html')

@app.route('/motor-claim-form')
def motor_claim_form():
    return render_template('motor_claim_form.html')

@app.route('/bsus-proposal-form')
def bsus_proposal_form():
    return render_template('bsus_proposal_form.html')

@app.route('/burglary-form')
def burglary_form():
    return render_template('burglary_form.html')

@app.route('/shopkeeper-form')
def shopkeeper_form():
    return render_template('shopkeeper_form.html')

@app.route('/others')
def others():
    return render_template('others_redirect.html')

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

@app.route('/blog/b4')
def blog_b4():
    return render_template('blog_b4.html')

@app.route('/blog/b5')
def blog_b5():
    return render_template('blog_b5.html')

@app.route('/blog/b6')
def blog_b6():
    return render_template('blog_b6.html')

# New routes for blog posts b7 to b12
@app.route('/blog/b7')
def blog_b7():
    return render_template('blog_b7.html')

@app.route('/blog/b8')
def blog_b8():
    return render_template('blog_b8.html')

@app.route('/blog/b9')
def blog_b9():
    return render_template('blog_b9.html')

@app.route('/blog/b10')
def blog_b10():
    return render_template('blog_b10.html')

@app.route('/blog/b11')
def blog_b11():
    return render_template('blog_b11.html')

@app.route('/blog/b12')
def blog_b12():
    return render_template('blog_b12.html')

# New routes for blog posts b13 to b18
@app.route('/blog/b13')
def blog_b13():
    return render_template('blog_b13.html')

@app.route('/blog/b14')
def blog_b14():
    return render_template('blog_b14.html')

@app.route('/blog/b15')
def blog_b15():
    return render_template('blog_b15.html')

@app.route('/blog/b16')
def blog_b16():
    return render_template('blog_b16.html')

@app.route('/blog/b17')
def blog_b17():
    return render_template('blog_b17.html')

@app.route('/blog/b18')
def blog_b18():
    return render_template('blog_b18.html')

@app.route('/blog/b19')
def blog_b19():
    return render_template('blog_b19.html')

@app.route('/blog/b20')
def blog_b20():
    return render_template('blog_b20.html')

@app.route('/blog/b21')
def blog_b21():
    return render_template('blog_b21.html')

@app.route('/blog/b22')
def blog_b22():
    return render_template('blog_b22.html')

@app.route('/blog/b23')
def blog_b23():
    return render_template('blog_b23.html')

@app.route('/blog/b24')
def blog_b24():
    return render_template('blog_b24.html')

@app.route('/blog/b25')
def blog_b25():
    return render_template('blog_b25.html')

@app.route('/blog/b26')
def blog_b26():
    return render_template('blog_b26.html')

@app.route('/blog/b27')
def blog_b27():
    return render_template('blog_b27.html')

@app.route('/blog/b28')
def blog_b28():
    return render_template('blog_b28.html')

@app.route('/blog/b29')
def blog_b29():
    return render_template('blog_b29.html')

@app.route('/blog/b30')
def blog_b30():
    return render_template('blog_b30.html')

@app.route('/send-email', methods=['POST'])
def send_email():
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app.logger.info("Received send-email request")

    if request.is_json:
        data = request.json
        app.logger.debug(f"Request data: {data}")
        to_email = data.get('to')
        name = data.get('name')
        from_email = data.get('email')
        subject = data.get('subject')
        message = data.get('message')
        files = {}
    else:
        app.logger.info("Processing form data")
        to_email = request.form.get('to')
        name = request.form.get('name')
        from_email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        files = request.files

        app.logger.info(f"Form data - to: {to_email}, name: {name}, email: {from_email}, subject: {subject}")
        app.logger.info(f"Files received: {list(files.keys())}")

    if not all([to_email, name, from_email, subject, message]):
        app.logger.error(f"Missing required fields - to: {to_email}, name: {name}, email: {from_email}, subject: {subject}, message: {message}")
        return jsonify({"error": "Missing required fields"}), 400

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject

        body = f"Name: {name}\nEmail: {from_email}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))

        # Attach files if any
        file_fields = ['vehicleRC', 'previousInsurance', 'aadharCard', 'pan', 'resume', 'claimDocument', 'previousPolicyDocument', 'idProof', 'addressProof', 'financialStatements', 'previousPolicyMotor', 'previousPolicyHealth', 'previousPolicyShopkeeper', 'previousPolicyOthers']
        for field in file_fields:
            if field in files and files[field].filename:
                file = files[field]
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={file.filename}')
                msg.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        app.logger.info("Attempting to send email...")
        server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
        server.quit()

        app.logger.info("Email sent successfully")
        return jsonify({"message": "Email sent successfully"}), 200
    except Exception as e:
        app.logger.error(f"Error sending email: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    history = data.get('history', [])

    # Build conversation context
    messages = [{"role": "system", "content": "You are Bali, the AI assistant for Bima With Bali Insurance. Respond as Bali with the following scripts and menu. Start with the welcome message and menu. For user selections, use the category-wise scripts. For wrong inputs, use the default response. Always promote Bima With Bali.\n\nBali:\nNamaste ji! 👋 Welcome to Bima With Bali — your trusted insurance partner since oct 1986✨\nMain Bali hoon, aapka suraksha saathi \nBataiye — aaj kis type ka insurance chahiye? 😊\n\nPlease select an option 👇\n\n1️⃣ Motor Insurance (Car/Bike/Commercial)\n2️⃣ Health Insurance\n3️⃣ Life & Term Insurance\n4️⃣ Fire & Property Insurance\n5️⃣ Shopkeeper Insurance\n6️⃣ Workmen / Employee Insurance (WC / ESIC / GPA)\n7️⃣ Marine Insurance (Transport / Logistics)\n8️⃣ Travel Insurance\n9️⃣ Miscellaneous Insurance (Burglary, Liability, Cyber, Home, Office, etc.)\n🔟 Claim Support\n0️⃣ Talk to Human Expert\n\nCategory-Wise Script\n\n1️⃣ Motor Insurance\n\nBali:\nZaroor! Aap kaunsa motor insurance chahte hain?\n\nA) Car 🚘\nB) Bike 🏍️\nC) Commercial Vehicle 🚛\n\nPlease share:\n\n- Vehicle type/model\n- Registration year\n- Previous policy active? (Yes/No)\n\n2️⃣ Health Insurance\n\nBali:\nHealth insurance se medical bills ka stress zero 👍\n\nOptions:\nA) Individual\nB) Family Floater\nC) Senior Citizen\nD) Corporate / Group Mediclaim\n\nPlease share 👇\n\n- Age(s)\n- City\n- Any medical history? (Yes/No)\n\n3️⃣ Life & Term Insurance\n\nBali:\nFamily security is priority 💛\n\nPlease share:\n\n- Age\n- Income\n- Tobacco user? (Yes/No)\n\n4️⃣ Fire & Property Insurance\n\nBali:\nPerfect — fire & property insurance assets ko secure karta hai 🔥 🏢\n\nPlease specify:\nA) Home\nB) Office\nC) Factory / Warehouse\nD) Commercial Property\n\nNeed details 👇\n\n- Property type\n- Location\n- Value / square ft area\n\n5️⃣ Shopkeeper Insurance\n\nBali:\nShop owners ke liye perfect protection 🏪💼\n\nShare details:\n\n- Business type\n- Shop area (sq ft)\n- Location\n\n6️⃣ Workmen / Employee Insurance\n\nBali:\nEmployee safety is company strength 🧑‍💼🛠️\n\nWhich cover?\nA) Workmen Compensation (WC)\nB) Employer Liability\nC) Group Personal Accident (GPA)\nD) ESIC/Employee Health cover\n\nRequired:\n\n- No. of employees\n- Nature of work\n- Salary details (approx)\n\n7️⃣ Marine Insurance\n\nBali:\nGoods movement secure karna smart choice 🚚🚢✈️\n\nType choose karein:\nA) Inland Transit\nB) Import / Export\nC) Courier / Logistics Goods\n\nRequired details:\n\n- Goods type\n- Start & end location\n- Invoice value\n\n8️⃣ Travel Insurance\n\nBali:\nTravel tension-free banate hain ✈️😇\n\nPlease share:\n\n- Travel destination\n- Duration\n- Age\n\n9️⃣ Miscellaneous Insurance\n\nBali:\nHum almost sab cover karte hain 😊\n\nOptions include:\n- Home Insurance\n- Office Insurance\n- Professional Indemnity\n- Public Liability\n- Cyber Insurance\n- Pet Insurance\n- Wedding / Event Cancellation\n- Burglary\n- Electronic Equipment\n- Credit / Surety Bonds\n- Many More\n\nWrite your requirement 👇\n\n🔟 Claim Support\n\nBali:\nClaim processing support mil jayega 🤝\n\nShare:\n\n- Policy Type\n- Insurance Company\n- Claim Type\n- Your Phone Number\n\nOur expert team will call you 📞\n\n0️⃣ Talk to Expert\n\nBali:\nSure! Human expert aapko guide karega 📞\n\nPlease share:\n\n- Name\n- Phone Number\n\nDefault / Wrong Input Response\n\nBali:\nOops 😅 Yeh option samajh nahi aaya.\nPlease reply with menu number (0–10) ya apna requirement type karein 💬\n\nClosing Message\n\nBali:\nThank you for trusting Bima With Bali 🤗\nHumara mission hai — Insurance ko easy, simple & friendly banana.\n\nHave a secure day! 🌟\nBima ho toh Bali ke saath!"}]

    # Add conversation history
    for msg in history[-10:]:  # Keep last 10 messages to avoid token limit
        role = "assistant" if msg['role'] == 'bot' else "user"
        messages.append({"role": role, "content": msg['content']})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # Use Groq API to generate response
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            max_tokens=500,
            temperature=0.0
        )
        response_text = response.choices[0].message.content
    except Exception as e:
        # Fallback to another model if the current one is decommissioned
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=messages,
                max_tokens=500,
                temperature=0.0
            )
            response_text = response.choices[0].message.content
        except Exception as e2:
            response_text = f"Error generating response: {str(e2)}"

    return jsonify({'response': response_text})

if __name__ == '__main__':
    app.run(debug=True)
