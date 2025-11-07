import os
from dotenv import load_dotenv
from groq import Groq
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, flash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import pymongo
from werkzeug.security import generate_password_hash, check_password_hash
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'bali_admin_secret_key_2024')
app.permanent_session_lifetime = timedelta(hours=24)

# Set file upload limits (16MB max per request, 5MB per file)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
import os
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'submissions'), exist_ok=True)

# File extensions allowed
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'csv', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# MongoDB configuration
from urllib.parse import quote_plus
MONGODB_URI = f"mongodb+srv://bali:{quote_plus('bali@123')}@cluster0.xu1iuqe.mongodb.net/"
DATABASE_NAME = "bali_insurance"

# MongoDB connection
try:
    client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    # Test connection
    client.admin.command('ping')
    db = client[DATABASE_NAME]
    logger.info("✅ MongoDB Atlas connected successfully")
except pymongo.errors.ServerSelectionTimeoutError:
    logger.error("❌ MongoDB Atlas connection failed - check your connection string")
    client = None
    db = None
except Exception as e:
    logger.error(f"❌ MongoDB Atlas error: {e}")
    client = None
    db = None

# MongoDB collections
def get_collections():
    """Get MongoDB collections"""
    if db is None:
        return None, None, None
    return (
        db.form_submissions,
        db.blog_posts,
        db.admin_sessions
    )

# Configure Groq API safely
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize Groq client: {e}")
        groq_client = None
else:
    groq_client = None
    logger.warning("GROQ_API_KEY not found. AI features will be disabled.")

# Admin credentials
ADMIN_USERNAME = "bali"
ADMIN_PASSWORD_HASH = generate_password_hash("bali@123")

# Email server configuration (with error handling)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "sparksolutionfreelancing@gmail.com"
SMTP_PASSWORD = "oqny rnem dbap yofq "

# Database functions
def get_db_connection():
    """Get database connection (MongoDB)"""
    return db

def init_db():
    """Initialize MongoDB collections with indexes"""
    try:
        if db is None:
            logger.error("MongoDB connection not available")
            return False
        
        form_submissions, blog_posts, admin_sessions = get_collections()
        
        # Create indexes for form_submissions
        form_submissions.create_index([("submission_date", pymongo.DESCENDING)])
        form_submissions.create_index([("status", pymongo.ASCENDING)])
        form_submissions.create_index([("insurance_type", pymongo.ASCENDING)])
        form_submissions.create_index([("email", pymongo.ASCENDING)])
        
        # Create indexes for blog_posts
        blog_posts.create_index([("slug", pymongo.ASCENDING)], unique=True)
        blog_posts.create_index([("status", pymongo.ASCENDING)])
        blog_posts.create_index([("published_date", pymongo.DESCENDING)])
        blog_posts.create_index([("created_date", pymongo.DESCENDING)])
        blog_posts.create_index([("tags", pymongo.ASCENDING)])
        
        # Create indexes for admin_sessions
        admin_sessions.create_index([("session_id", pymongo.ASCENDING)], unique=True)
        admin_sessions.create_index([("login_time", pymongo.DESCENDING)])
        admin_sessions.create_index([("admin_user", pymongo.ASCENDING)])
        
        logger.info("✅ MongoDB collections and indexes initialized successfully")
        return True
    except Exception as e:
        logger.error(f"MongoDB initialization error: {e}")
        return False

def cleanup_audit_log():
    """Keep only the top 5 most recent audit log entries"""
    try:
        form_submissions, blog_posts, admin_sessions = get_collections()
        if admin_sessions is not None:
            # Get the 6th most recent entry
            sessions = admin_sessions.find().sort("login_time", pymongo.DESCENDING).skip(5).limit(1)
            sixth_entry = sessions.first()
            
            if sixth_entry:
                # Delete all entries older than the 6th most recent
                admin_sessions.delete_many({"_id": {"$lt": sixth_entry["_id"]}})
    except Exception as e:
        app.logger.error(f"Error cleaning up audit log: {e}")

# Authentication decorator
def admin_required(f):
    """Decorator to require admin authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize database on startup
try:
    db_initialized = init_db()
    if db_initialized:
        app.logger.info("✅ Database initialized successfully")
    else:
        app.logger.error("❌ Database initialization failed")
except Exception as e:
    app.logger.error(f"❌ Database startup error: {e}")

# Test imports
try:
    from groq import Groq
    app.logger.info("✅ Groq import successful")
except ImportError as e:
    app.logger.warning(f"⚠️ Groq import failed: {e}")

try:
    import smtplib
    app.logger.info("✅ SMTP import successful")
except ImportError as e:
    app.logger.error("❌ SMTP import failed: {e}")

# File storage utilities
def save_uploaded_file(file, submission_id, field_name):
    """Save uploaded file to submissions folder and return file path"""
    if not file or not file.filename:
        return None
    
    try:
        # Create safe filename
        import uuid
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        safe_filename = f"{submission_id}_{field_name}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Save file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'submissions', safe_filename)
        file.save(file_path)
        
        app.logger.info(f"Saved file: {safe_filename}")
        return f"submissions/{safe_filename}"
    except Exception as e:
        app.logger.error(f"Error saving file {field_name}: {e}")
        return None

# Static files and favicon
@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except:
        # Return a simple 204 response if favicon doesn't exist
        return '', 204

@app.route('/favicon.png')
def favicon_png():
    try:
        return send_from_directory('static', 'favicon.png', mimetype='image/png')
    except:
        # Return a simple 204 response if favicon doesn't exist
        return '', 204

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# File serving route for uploaded files
@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER']), filename)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Basic website routes
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

@app.route('/miscellaneous')
def miscellaneous():
    return render_template('miscellaneous.html')

@app.route('/renewal')
def renewal():
    return render_template('renewal.html')

@app.route('/career')
def career():
    return render_template('career.html')

# Test route to verify server is working
@app.route('/test')
def test():
    return jsonify({"status": "Server is working", "time": datetime.now().isoformat()}), 200

@app.route('/blog')
def blog():
    """Display all blog posts"""
    form_submissions, blog_posts, admin_sessions = get_collections()
    posts = list(blog_posts.find({"status": "published"}).sort([("published_date", pymongo.DESCENDING), ("created_date", pymongo.DESCENDING)]))
    return render_template('blog.html', posts=posts)

@app.route('/blog/<slug>')
def blog_post(slug):
    """Display single blog post"""
    form_submissions, blog_posts, admin_sessions = get_collections()
    post = blog_posts.find_one({"slug": slug, "status": "published"})
    
    related_posts = []
    if post:
        if post.get('tags'):
            tags = post['tags'].split(',')
            related_posts = list(blog_posts.find({
                "status": "published",
                "_id": {"$ne": post["_id"]},
                "tags": {"$regex": tags[0].strip(), "$options": "i"}
            }).limit(3))
        
        if not related_posts:
            related_posts = list(blog_posts.find({
                "status": "published",
                "_id": {"$ne": post["_id"]}
            }).sort([("published_date", pymongo.DESCENDING), ("created_date", pymongo.DESCENDING)]).limit(3))
    
    if not post:
        return render_template('blog_single.html', post=None, related_posts=[]), 404
    
    return render_template('blog_single.html', post=post, related_posts=related_posts)

# Static Blog Post Routes
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
    app.logger.info("=== SEND EMAIL FUNCTION CALLED ===")
    
    try:
        # Check if this is a JSON request (API) or form request
        if request.is_json:
            app.logger.info("Processing JSON request")
            data = request.json
            to_email = data.get('to')
            name = data.get('name')
            from_email = data.get('email')
            subject = data.get('subject')
            message = data.get('message')
            files = {}
            is_form_submission = False
        else:
            app.logger.info("Processing FORM request")
            to_email = request.form.get('to')
            name = request.form.get('name')
            from_email = request.form.get('email')
            subject = request.form.get('subject')
            message = request.form.get('message')
            files = request.files
            
            # Check if this is a renewal form submission
            is_form_submission = 'insuranceType' in request.form
            app.logger.info(f"Is renewal form submission: {is_form_submission}")
            app.logger.info(f"Form keys: {list(request.form.keys())}")

        app.logger.info(f"Required fields check - to: {bool(to_email)}, name: {bool(name)}, from: {bool(from_email)}, subject: {bool(subject)}, message: {bool(message)}")

        # Validate required fields
        if not all([to_email, name, from_email, subject, message]):
            app.logger.error(f"Missing required fields - to: {to_email}, name: {name}, email: {from_email}, subject: {subject}, message: {message}")
            return jsonify({"error": "Missing required fields"}), 400

        # Handle renewal form submission
        if is_form_submission:
            app.logger.info("=== PROCESSING RENEWAL FORM SUBMISSION ===")
            
            try:
                # Extract form data
                first_name = request.form.get('firstName', '')
                last_name = request.form.get('lastName', '')
                phone = request.form.get('phone', '')
                email = request.form.get('email', '')
                want_to = "renewal"
                insurance_type = request.form.get('insuranceType', '')
                date_of_birth = request.form.get('dateOfBirth', '')
                aadhaar = request.form.get('aadhaar', '')
                
                # Extract dynamic fields
                vehicle_rc = request.form.get('vehicleRC', '')
                previous_policy_motor = request.form.get('previousPolicyMotor', '')
                previous_policy_health = request.form.get('previousPolicyHealth', '')
                pre_existing_disease = request.form.get('preExistingDisease', '')
                travel_country = request.form.get('travelCountry', '')
                travel_duration = request.form.get('travelDuration', '')
                travel_age = request.form.get('travelAge', '')
                commodity_type = request.form.get('commodityType', '')
                transport_mode = request.form.get('transportMode', '')
                pre_carrying_unit = request.form.get('preCarryingUnit', '')
                business_nature = request.form.get('businessNature', '')
                previous_policy_shopkeeper = request.form.get('previousPolicyShopkeeper', '')
                claim_occurred = request.form.get('claimOccurred', '')
                number_of_members = request.form.get('numberOfMembers', '')
                salary = request.form.get('salary', '')
                work_nature = request.form.get('workNature', '')
                sum_insured = request.form.get('sumInsured', '')
                locality = request.form.get('locality', '')
                pincode = request.form.get('pincode', '')
                occupancy = request.form.get('occupancy', '')
                type_of_insurance = request.form.get('typeOfInsurance', '')
                previous_policy_others = request.form.get('previousPolicyOthers', '')
                
                app.logger.info(f"Form data extracted - Name: {first_name} {last_name}, Insurance: {insurance_type}")
                
                # Save to database
                form_submissions, blog_posts, admin_sessions = get_collections()
                if form_submissions is not None:
                    try:
                        app.logger.info("Attempting database insert...")
                        
                        # Create submission document
                        submission_doc = {
                            "first_name": first_name,
                            "last_name": last_name,
                            "phone": phone,
                            "email": email,
                            "want_to": want_to,
                            "insurance_type": insurance_type,
                            "date_of_birth": date_of_birth,
                            "aadhaar": aadhaar,
                            "vehicle_rc": vehicle_rc,
                            "previous_policy_motor": previous_policy_motor,
                            "previous_policy_health": previous_policy_health,
                            "pre_existing_disease": pre_existing_disease,
                            "travel_country": travel_country,
                            "travel_duration": travel_duration,
                            "travel_age": travel_age,
                            "commodity_type": commodity_type,
                            "transport_mode": transport_mode,
                            "pre_carrying_unit": pre_carrying_unit,
                            "business_nature": business_nature,
                            "previous_policy_shopkeeper": previous_policy_shopkeeper,
                            "claim_occurred": claim_occurred,
                            "number_of_members": number_of_members,
                            "salary": salary,
                            "work_nature": work_nature,
                            "sum_insured": sum_insured,
                            "locality": locality,
                            "pincode": pincode,
                            "occupancy": occupancy,
                            "type_of_insurance": type_of_insurance,
                            "previous_policy_others": previous_policy_others,
                            "submission_date": datetime.now(),
                            "status": "new"
                        }
                        
                        result = form_submissions.insert_one(submission_doc)
                        submission_id = result.inserted_id
                        app.logger.info(f"Submission created with ID: {submission_id}")
                        
                        # Save uploaded files
                        saved_files = {}
                        file_fields = {
                            'vehicleRC': 'vehicle_rc_file',
                            'previousPolicyMotor': 'previous_policy_motor_file',
                            'previousPolicyHealth': 'previous_policy_health_file',
                            'previousPolicyShopkeeper': 'previous_policy_shopkeeper_file',
                            'previousPolicyOthers': 'previous_policy_others_file'
                        }
                        
                        for field_name, db_column in file_fields.items():
                            if field_name in files and files[field_name].filename:
                                file_path = save_uploaded_file(files[field_name], submission_id, field_name)
                                if file_path:
                                    saved_files[field_name] = file_path
                                    form_submissions.update_one(
                                        {"_id": submission_id},
                                        {"$set": {db_column: file_path}}
                                    )
                        
                        app.logger.info(f"Files saved: {saved_files}")
                        app.logger.info("Database insert with file storage successful")
                    except Exception as db_error:
                        app.logger.error(f"Database error: {db_error}")
                        raise db_error
                
                # Send admin notification email
                try:
                    admin_msg = MIMEMultipart()
                    admin_msg['From'] = SMTP_USERNAME
                    admin_msg['To'] = "sparksolutionfreelancing@gmail.com"
                    admin_msg['Subject'] = f"New Renewal Form Submission - {insurance_type}"
                    
                    admin_body = f"""New renewal form submission received:

Name: {first_name} {last_name}
Email: {email}
Phone: {phone}
Date of Birth: {date_of_birth}
Insurance Type: {insurance_type}
Aadhaar: {aadhaar}

Submission Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                    admin_msg.attach(MIMEText(admin_body, 'plain'))
                    
                    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                    server.starttls()
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                    server.sendmail(SMTP_USERNAME, "sparksolutionfreelancing@gmail.com", admin_msg.as_string())
                    server.quit()
                    app.logger.info("Admin notification sent successfully")
                except Exception as email_error:
                    app.logger.error(f"Admin notification failed: {email_error}")
                    # Don't fail the whole request if email fails
                    
            except Exception as form_error:
                app.logger.error(f"Form processing error: {form_error}")
                raise form_error

        # Send main email
        try:
            app.logger.info("Sending main email...")
            msg = MIMEMultipart()
            msg['From'] = SMTP_USERNAME
            msg['To'] = to_email
            msg['Subject'] = subject

            body = f"Name: {name}\nEmail: {from_email}\n\nMessage:\n{message}"
            msg.attach(MIMEText(body, 'plain'))

            # Handle file attachments for form submissions
            if is_form_submission:
                file_fields = ['vehicleRC', 'previousPolicyMotor', 'previousPolicyHealth', 'previousPolicyShopkeeper', 'previousPolicyOthers']
                for field in file_fields:
                    if field in files and files[field].filename:
                        try:
                            file = files[field]
                            # Validate file size
                            file.seek(0, 2)
                            file_size = file.tell()
                            file.seek(0)
                            
                            if file_size > 5 * 1024 * 1024:  # 5MB
                                app.logger.error(f"File {file.filename} exceeds 5MB limit")
                                return jsonify({"error": f"File {file.filename} is too large. Maximum size allowed is 5MB."}), 400
                            
                            # Validate file extension
                            if not allowed_file(file.filename):
                                app.logger.error(f"File {file.filename} has invalid extension")
                                return jsonify({"error": f"File {file.filename} has invalid extension. Only PDF and image files are allowed."}), 400
                            
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(file.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename={file.filename}')
                            msg.attach(part)
                            app.logger.info(f"Attached file: {file.filename}")
                        except Exception as file_error:
                            app.logger.error(f"Error processing file {field}: {file_error}")

            # Send email
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
            server.quit()

            app.logger.info("Email sent successfully")
            
            # Return success response
            if is_form_submission:
                return jsonify({"message": "Renewal form submitted successfully! Our team will contact you shortly."}), 200
            else:
                return jsonify({"message": "Email sent successfully"}), 200
                
        except Exception as email_error:
            app.logger.error(f"Main email sending failed: {email_error}")
            # If this was a form submission, still return success since we saved to database
            if is_form_submission:
                return jsonify({"message": "Form submitted successfully. Email delivery may be delayed."}), 200
            else:
                return jsonify({"error": "Email sending failed. Please try again later."}), 500
            
    except Exception as e:
        app.logger.error(f"CRITICAL ERROR in send_email: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    history = data.get('history', [])

    # Check if Groq client is available
    if groq_client is None:
        return jsonify({'response': "I'm sorry, but the AI assistant is currently unavailable. Please contact our team directly for assistance with your insurance needs."})

    # Build conversation context
    messages = [{"role": "system", "content": "You are Bali, the AI assistant for Bima With Bali Insurance. Respond as Bali with the following scripts and menu. Start with the welcome message and menu. For user selections, use the category-wise scripts. For wrong inputs, use the default response. Always promote Bima With Bali."}]

    # Add conversation history
    for msg in history[-10:]:  # Keep last 10 messages to avoid token limit
        role = "assistant" if msg['role'] == 'bot' else "user"
        messages.append({"role": role, "content": msg['content']})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # Use Groq API to generate response
    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            max_tokens=500,
            temperature=0.0
        )
        response_text = response.choices[0].message.content
    except Exception as e:
        # Fallback to another model if the current one is decommissioned
        try:
            response = groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=messages,
                max_tokens=500,
                temperature=0.0
            )
            response_text = response.choices[0].message.content
        except Exception as e2:
            logger.error(f"Groq API error: {e2}")
            response_text = "I'm sorry, but I'm having trouble connecting right now. Please try again later or contact our team directly for immediate assistance."

    return jsonify({'response': response_text})

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page with error handling"""
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
                session['admin_logged_in'] = True
                session['admin_username'] = username
                session.permanent = True
                
                # Generate a unique session ID
                import uuid
                session_id = str(uuid.uuid4())
                
                # Log admin session (with error handling)
                try:
                    form_submissions, blog_posts, admin_sessions = get_collections()
                    if admin_sessions is not None:
                        session_doc = {
                            "session_id": session_id,
                            "admin_user": username,
                            "login_time": datetime.now(),
                            "last_activity": datetime.now(),
                            "ip_address": request.remote_addr,
                            "user_agent": request.headers.get('User-Agent')
                        }
                        admin_sessions.insert_one(session_doc)
                        
                        # Cleanup audit log to keep only top 5
                        cleanup_audit_log()
                except Exception as e:
                    app.logger.error(f"Failed to log admin session: {e}")
                
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('admin/login.html')
    except Exception as e:
        app.logger.error(f"Admin login error: {e}")
        flash('System error. Please try again later.', 'error')
        return render_template('admin/login.html')

@app.route('/admin/logout')
@admin_required
def admin_logout():
    """Admin logout"""
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard with key metrics and error handling"""
    try:
        form_submissions, blog_posts, admin_sessions = get_collections()
        if form_submissions is None or blog_posts is None:
            return render_template('admin/dashboard.html',
                                 total_submissions=0,
                                 new_submissions=0,
                                 total_blog_posts=0,
                                 published_posts=0,
                                 recent_submissions=[],
                                 submissions_by_type=[],
                                 monthly_trends=[])
        
        # Get dashboard statistics with error handling
        try:
            total_submissions = form_submissions.count_documents({})
        except:
            total_submissions = 0
            
        try:
            new_submissions = form_submissions.count_documents({"status": "new"})
        except:
            new_submissions = 0
            
        try:
            total_blog_posts = blog_posts.count_documents({})
        except:
            total_blog_posts = 0
            
        try:
            published_posts = blog_posts.count_documents({"status": "published"})
        except:
            published_posts = 0
        
        # Get recent submissions
        try:
            recent_submissions = list(form_submissions.find({}).sort("submission_date", pymongo.DESCENDING).limit(10))
        except:
            recent_submissions = []
        
        # Get submissions by insurance type
        try:
            pipeline = [
                {"$group": {"_id": "$insurance_type", "count": {"$sum": 1}}},
                {"$sort": {"count": pymongo.DESCENDING}}
            ]
            submissions_by_type = list(form_submissions.aggregate(pipeline))
        except:
            submissions_by_type = []
        
        # Get monthly submission trends
        try:
            pipeline = [
                {"$match": {"submission_date": {"$gte": datetime.now() - timedelta(days=365)}}},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m", "date": "$submission_date"}},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": pymongo.DESCENDING}}
            ]
            monthly_trends = list(form_submissions.aggregate(pipeline))
        except:
            monthly_trends = []
        
        return render_template('admin/dashboard.html',
                             total_submissions=total_submissions,
                             new_submissions=new_submissions,
                             total_blog_posts=total_blog_posts,
                             published_posts=published_posts,
                             recent_submissions=recent_submissions,
                             submissions_by_type=submissions_by_type,
                             monthly_trends=monthly_trends)
    except Exception as e:
        app.logger.error(f"Admin dashboard error: {e}")
        return render_template('admin/dashboard.html',
                             total_submissions=0,
                             new_submissions=0,
                             total_blog_posts=0,
                             published_posts=0,
                             recent_submissions=[],
                             submissions_by_type=[],
                             monthly_trends=[])

@app.route('/admin/submissions')
@admin_required
def admin_submissions():
    """Manage form submissions"""
    # Get filter parameters
    status_filter = request.args.get('status', '')
    insurance_type_filter = request.args.get('insurance_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query
    form_submissions, blog_posts, admin_sessions = get_collections()
    query = {}
    
    if status_filter:
        query["status"] = status_filter
    
    if insurance_type_filter:
        query["insurance_type"] = insurance_type_filter
    
    if date_from:
        query["submission_date"] = {"$gte": datetime.strptime(date_from, "%Y-%m-%d")}
    
    if date_to:
        if "submission_date" not in query:
            query["submission_date"] = {}
        query["submission_date"]["$lte"] = datetime.strptime(date_to, "%Y-%m-%d")
    
    if search_query:
        query["$or"] = [
            {"first_name": {"$regex": search_query, "$options": "i"}},
            {"last_name": {"$regex": search_query, "$options": "i"}},
            {"email": {"$regex": search_query, "$options": "i"}},
            {"phone": {"$regex": search_query, "$options": "i"}}
        ]
    
    # Get total count for pagination
    total_count = form_submissions.count_documents(query) if form_submissions is not None else 0
    
    # Get paginated results
    submissions = list(form_submissions.find(query).sort("submission_date", pymongo.DESCENDING).skip((page - 1) * per_page).limit(per_page)) if form_submissions is not None else []
    
    # Get filter options
    insurance_types = list(form_submissions.distinct("insurance_type")) if form_submissions is not None else []
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('admin/submissions.html',
                         submissions=submissions,
                         insurance_types=insurance_types,
                         current_page=page,
                         total_pages=total_pages,
                         total_count=total_count,
                         filters={
                             'status': status_filter,
                             'insurance_type': insurance_type_filter,
                             'date_from': date_from,
                             'date_to': date_to,
                             'search': search_query
                         })

@app.route('/admin/submissions/<submission_id>')
@admin_required
def admin_submission_detail(submission_id):
    """View submission detail"""
    form_submissions, blog_posts, admin_sessions = get_collections()
    submission = form_submissions.find_one({"_id": pymongo.ObjectId(submission_id)}) if form_submissions is not None else None
    
    if not submission:
        flash('Submission not found', 'error')
        return redirect(url_for('admin_submissions'))
    
    return render_template('admin/submission_detail.html', submission=submission)

@app.route('/admin/submissions/<submission_id>/update', methods=['POST'])
@admin_required
def admin_update_submission(submission_id):
    """Update submission status and notes"""
    try:
        if request.is_json:
            data = request.json
            status = data.get('status')
            notes = data.get('notes')
        else:
            status = request.form.get('status')
            notes = request.form.get('notes')
        
        if not status:
            return jsonify({"success": False, "message": "Status is required"}), 400
        
        form_submissions, blog_posts, admin_sessions = get_collections()
        update_data = {
            "status": status,
            "notes": notes,
            "processed_by": session['admin_username'],
            "processed_date": datetime.now()
        }
        form_submissions.update_one({"_id": pymongo.ObjectId(submission_id)}, {"$set": update_data}) if form_submissions is not None else None
        
        if request.is_json:
            return jsonify({"success": True, "message": "Submission updated successfully"})
        else:
            flash('Submission updated successfully', 'success')
            return redirect(url_for('admin_submission_detail', submission_id=submission_id))
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/admin/submissions/<submission_id>/delete', methods=['POST'])
@admin_required
def admin_delete_submission(submission_id):
    """Delete a submission completely from database"""
    try:
        form_submissions, blog_posts, admin_sessions = get_collections()
        
        # Check if submission exists
        submission = form_submissions.find_one({"_id": pymongo.ObjectId(submission_id)}) if form_submissions is not None else None
        
        if not submission:
            return jsonify({"success": False, "message": "Submission not found"}), 404
        
        # Delete the submission
        form_submissions.delete_one({"_id": pymongo.ObjectId(submission_id)}) if form_submissions is not None else None
        
        # Log the deletion in audit log
        try:
            if admin_sessions is not None:
                session_doc = {
                    "session_id": f"deleted_submission_{submission_id}",
                    "admin_user": session['admin_username'],
                    "login_time": datetime.now(),
                    "last_activity": datetime.now(),
                    "ip_address": request.remote_addr,
                    "user_agent": f"Deleted submission {submission_id} - {submission.get('first_name', '')} {submission.get('last_name', '')}"
                }
                admin_sessions.insert_one(session_doc)
                cleanup_audit_log()
        except Exception as e:
            app.logger.error(f"Failed to log deletion: {e}")
        
        return jsonify({"success": True, "message": "Submission deleted successfully"})
    except Exception as e:
        app.logger.error(f"Error deleting submission {submission_id}: {e}")
        return jsonify({"success": False, "message": "An error occurred while deleting the submission"}), 500

@app.route('/admin/blog')
@admin_required
def admin_blog():
    """Manage blog posts"""
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    form_submissions, blog_posts, admin_sessions = get_collections()
    query = {}
    
    if status_filter:
        query["status"] = status_filter
    
    if search_query:
        query["$or"] = [
            {"title": {"$regex": search_query, "$options": "i"}},
            {"content": {"$regex": search_query, "$options": "i"}}
        ]
    
    # Get total count
    total_count = blog_posts.count_documents(query) if blog_posts is not None else 0
    
    # Get paginated results
    posts = list(blog_posts.find(query).sort("created_date", pymongo.DESCENDING).skip((page - 1) * per_page).limit(per_page)) if blog_posts is not None else []
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('admin/blog.html',
                         posts=posts,
                         current_page=page,
                         total_pages=total_pages,
                         total_count=total_count,
                         status_filter=status_filter,
                         search_query=search_query)

@app.route('/admin/blog/new', methods=['GET', 'POST'])
@admin_required
def admin_blog_new():
    """Create new blog post"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        excerpt = request.form.get('excerpt')
        status = request.form.get('status')
        featured_image = request.form.get('featured_image')
        tags = request.form.get('tags')
        meta_description = request.form.get('meta_description')
        
        # Generate slug from title
        slug = title.lower().replace(' ', '-').replace(',', '').replace('.', '')
        
        form_submissions, blog_posts, admin_sessions = get_collections()
        try:
            post_doc = {
                "title": title,
                "slug": slug,
                "content": content,
                "excerpt": excerpt,
                "status": status,
                "featured_image": featured_image,
                "tags": tags,
                "meta_description": meta_description,
                "author": "Bima With Bali",
                "created_date": datetime.now(),
                "updated_date": datetime.now()
            }
            
            if status == "published":
                post_doc["published_date"] = datetime.now()
            
            blog_posts.insert_one(post_doc) if blog_posts is not None else None
            flash('Blog post created successfully', 'success')
            return redirect(url_for('admin_blog'))
        except pymongo.errors.DuplicateKeyError:
            flash('A blog post with this title already exists', 'error')
    
    return render_template('admin/blog_new.html')

@app.route('/admin/blog/<post_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_blog_edit(post_id):
    """Edit blog post"""
    form_submissions, blog_posts, admin_sessions = get_collections()
    post = blog_posts.find_one({"_id": pymongo.ObjectId(post_id)}) if blog_posts is not None else None
    
    if not post:
        flash('Blog post not found', 'error')
        return redirect(url_for('admin_blog'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        excerpt = request.form.get('excerpt')
        status = request.form.get('status')
        featured_image = request.form.get('featured_image')
        tags = request.form.get('tags')
        meta_description = request.form.get('meta_description')
        
        # Generate slug from title
        slug = title.lower().replace(' ', '-').replace(',', '').replace('.', '')
        
        try:
            update_data = {
                "title": title,
                "slug": slug,
                "content": content,
                "excerpt": excerpt,
                "status": status,
                "featured_image": featured_image,
                "tags": tags,
                "meta_description": meta_description,
                "updated_date": datetime.now()
            }
            
            # Set published date if status is published
            if status == "published" and post.get("status") != "published":
                update_data["published_date"] = datetime.now()
            
            blog_posts.update_one({"_id": pymongo.ObjectId(post_id)}, {"$set": update_data}) if blog_posts is not None else None
            flash('Blog post updated successfully', 'success')
            return redirect(url_for('admin_blog'))
        except pymongo.errors.DuplicateKeyError:
            flash('A blog post with this title already exists', 'error')
    
    return render_template('admin/blog_edit.html', post=post)

@app.route('/admin/blog/<post_id>/status', methods=['POST'])
@admin_required
def admin_blog_status(post_id):
    """Update blog post status"""
    data = request.json
    new_status = data.get('status')
    
    form_submissions, blog_posts, admin_sessions = get_collections()
    post = blog_posts.find_one({"_id": pymongo.ObjectId(post_id)}) if blog_posts is not None else None
    
    if post:
        update_data = {"status": new_status, "updated_date": datetime.now()}
        
        # Set published date if status is published
        if new_status == "published":
            update_data["published_date"] = datetime.now()
        
        blog_posts.update_one({"_id": pymongo.ObjectId(post_id)}, {"$set": update_data}) if blog_posts is not None else None
        
        return jsonify({"success": True, "message": "Status updated successfully"})
    else:
        return jsonify({"success": False, "message": "Post not found"})

@app.route('/admin/blog/<post_id>/delete', methods=['POST'])
@admin_required
def admin_blog_delete(post_id):
    """Delete blog post"""
    form_submissions, blog_posts, admin_sessions = get_collections()
    post = blog_posts.find_one({"_id": pymongo.ObjectId(post_id)}) if blog_posts is not None else None
    
    if post:
        blog_posts.delete_one({"_id": pymongo.ObjectId(post_id)}) if blog_posts is not None else None
        return jsonify({'success': True, 'message': 'Blog post deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Blog post not found'}), 404

@app.route('/admin/export/submissions')
@admin_required
def admin_export_submissions():
    """Export submissions to CSV"""
    import csv
    from io import StringIO
    
    form_submissions, blog_posts, admin_sessions = get_collections()
    submissions = list(form_submissions.find({}).sort("submission_date", pymongo.DESCENDING)) if form_submissions is not None else []
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'First Name', 'Last Name', 'Phone', 'Email', 'Want To', 'Insurance Type', 'Date of Birth', 'Aadhaar',
                    'Vehicle RC', 'Previous Policy Motor', 'Previous Policy Health', 'Pre-existing Disease',
                    'Travel Country', 'Travel Duration', 'Travel Age', 'Commodity Type', 'Transport Mode', 'Pre-carrying Unit',
                    'Business Nature', 'Previous Policy Shopkeeper', 'Claim Occurred', 'Number of Members', 'Salary', 'Work Nature',
                    'Sum Insured', 'Locality', 'Pincode', 'Occupancy', 'Type of Insurance', 'Previous Policy Others',
                    'Vehicle RC File', 'Previous Policy Motor File', 'Previous Policy Health File', 'Previous Policy Shopkeeper File', 'Previous Policy Others File',
                    'Submission Date', 'Status', 'Notes', 'Processed By', 'Processed Date'])
    
    # Write data
    for submission in submissions:
        # Helper function to safely get column values
        def safe_get(field_name, default=''):
            return submission.get(field_name, default) or default
        
        # Get date of birth (fallback to age for backward compatibility)
        date_of_birth = safe_get('date_of_birth')
        if not date_of_birth:
            date_of_birth = safe_get('age')  # fallback for old submissions
        
        writer.writerow([
            str(submission.get('_id', '')),
            submission.get('first_name', ''),
            submission.get('last_name', ''),
            submission.get('phone', ''),
            submission.get('email', ''),
            submission.get('want_to', ''),
            submission.get('insurance_type', ''),
            date_of_birth,
            submission.get('aadhaar', ''),
            submission.get('vehicle_rc', ''),
            submission.get('previous_policy_motor', ''),
            submission.get('previous_policy_health', ''),
            submission.get('pre_existing_disease', ''),
            submission.get('travel_country', ''),
            submission.get('travel_duration', ''),
            submission.get('travel_age', ''),
            submission.get('commodity_type', ''),
            submission.get('transport_mode', ''),
            submission.get('pre_carrying_unit', ''),
            submission.get('business_nature', ''),
            submission.get('previous_policy_shopkeeper', ''),
            submission.get('claim_occurred', ''),
            submission.get('number_of_members', ''),
            submission.get('salary', ''),
            submission.get('work_nature', ''),
            submission.get('sum_insured', ''),
            submission.get('locality', ''),
            submission.get('pincode', ''),
            submission.get('occupancy', ''),
            submission.get('type_of_insurance', ''),
            submission.get('previous_policy_others', ''),
            safe_get('vehicle_rc_file'),
            safe_get('previous_policy_motor_file'),
            safe_get('previous_policy_health_file'),
            safe_get('previous_policy_shopkeeper_file'),
            safe_get('previous_policy_others_file'),
            submission.get('submission_date', '').strftime('%Y-%m-%d %H:%M:%S') if submission.get('submission_date') else '',
            submission.get('status', ''),
            submission.get('notes', ''),
            submission.get('processed_by', ''),
            submission.get('processed_date', '').strftime('%Y-%m-%d %H:%M:%S') if submission.get('processed_date') else ''
        ])
    
    output.seek(0)
    
    response = app.response_class(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=submissions.csv'}
    )
    
    return response

@app.route('/admin/audit-log')
@admin_required
def admin_audit_log():
    """Admin audit log page - shows only top 5 entries"""
    # Always cleanup before showing
    cleanup_audit_log()
    
    form_submissions, blog_posts, admin_sessions = get_collections()
    # Get top 5 admin sessions for audit log
    sessions = list(admin_sessions.find({}).sort("login_time", pymongo.DESCENDING).limit(5)) if admin_sessions is not None else []
    
    # Transform sessions to match template expectations
    logs = []
    for session in sessions:
        log_entry = {
            'id': str(session.get('_id', '')),
            'action': 'LOGIN',
            'table_name': 'admin_sessions',
            'record_id': str(session.get('_id', '')),
            'admin_user': session.get('admin_user', ''),
            'ip_address': session.get('ip_address', ''),
            'timestamp': session.get('login_time', '').strftime('%Y-%m-%d %H:%M:%S') if session.get('login_time') else '',
            'old_values': None,
            'new_values': f"Session ID: {session.get('session_id', '')}, User Agent: {session.get('user_agent', '')}"
        }
        logs.append(log_entry)
    
    return render_template('admin/audit_log.html',
                         logs=logs,
                         current_page=1,
                         total_pages=1,
                         total_count=len(logs))

@app.route('/admin/export/audit-log')
@admin_required
def admin_export_audit_log():
    """Export top 5 audit log entries to CSV"""
    import csv
    from io import StringIO
    
    # Cleanup before export
    cleanup_audit_log()
    
    form_submissions, blog_posts, admin_sessions = get_collections()
    # Export only top 5 sessions
    sessions = list(admin_sessions.find({}).sort("login_time", pymongo.DESCENDING).limit(5)) if admin_sessions is not None else []
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Admin User', 'Session ID', 'Login Time', 'Last Activity', 'IP Address', 'User Agent'])
    
    # Write data
    for session in sessions:
        writer.writerow([
            str(session.get('_id', '')),
            session.get('admin_user', ''),
            session.get('session_id', ''),
            session.get('login_time', '').strftime('%Y-%m-%d %H:%M:%S') if session.get('login_time') else '',
            session.get('last_activity', '').strftime('%Y-%m-%d %H:%M:%S') if session.get('last_activity') else '',
            session.get('ip_address', ''),
            session.get('user_agent', '')
        ])
    
    output.seek(0)
    
    response = app.response_class(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=audit_log.csv'}
    )
    
    return response

if __name__ == '__main__':
    app.run(debug=True)