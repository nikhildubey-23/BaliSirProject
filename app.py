import pymongo
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, flash, Response
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from functools import wraps
from bson import ObjectId
import json
import io
import csv
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'bali_admin_secret_key_2024')
app.permanent_session_lifetime = timedelta(hours=24)

# Mail configuration - support both MAIL_* and SMTP_* variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER') or os.getenv('SMTP_HOST')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT') or os.getenv('SMTP_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME') or os.getenv('SMTP_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD') or os.getenv('SMTP_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER') or os.getenv('SMTP_USERNAME')

mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

# Set file upload limits (16MB max per request, 5MB per file)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['UPLOAD_FOLDER'] = 'uploads'

# File extensions allowed
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'csv', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
mongo_client = None
mongo_db = None

def init_mongodb():
    global mongo_client, mongo_db
    mongodb_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("DATABASE_NAME")
    if not mongodb_uri or not database_name:
        logger.error("MONGODB_URI or DATABASE_NAME not set in environment variables.")
        return
    try:
        from pymongo import MongoClient
        mongo_client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        mongo_db = mongo_client[database_name]
        mongo_client.server_info()
        logger.info(f"✅ MongoDB connected successfully to database: {mongo_db.name}")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")

# Configure Groq API safely
# WARNING: Hardcoding API keys is a security risk. It is highly recommended to use environment variables instead.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize Groq client: {e}")
        client = None
else:
    client = None
    logger.warning("GROQ_API_KEY not found. AI features will be disabled.")

# Admin credentials
ADMIN_USERNAME = "bali"
# Load password hash from .env, or generate default if not present
env_password_hash = os.getenv('ADMIN_PASSWORD_HASH')
if env_password_hash:
    ADMIN_PASSWORD_HASH = env_password_hash
else:
    # Default password hash for initial setup
    ADMIN_PASSWORD_HASH = generate_password_hash("bali@123")
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', os.getenv('FORGET_PASSWORD_EMAIL', 'admin@example.com'))

def update_env_file(key, value):
    """Update a key-value pair in the .env file"""
    env_path = '.env'
    if not os.path.exists(env_path):
        logger.error(f".env file not found at {env_path}")
        return False
    
    try:
        # Read the current .env file
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update or add the key-value pair
        key_found = False
        updated_lines = []
        for line in lines:
            # Handle lines with or without spaces around =
            if line.strip().startswith(f'{key}=') or line.strip().startswith(f'{key} ='):
                updated_lines.append(f'{key}={value}\n')
                key_found = True
            else:
                updated_lines.append(line)
        
        # If key not found, add it at the end
        if not key_found:
            updated_lines.append(f'{key}={value}\n')
        
        # Write back to .env file
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)
        
        logger.info(f"Successfully updated {key} in .env file")
        return True
    except Exception as e:
        logger.error(f"Error updating .env file: {e}")
        return False

# Email server configuration (with error handling) - support both MAIL_* and SMTP_* variables
SMTP_SERVER = os.getenv('MAIL_SERVER') or os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('MAIL_PORT') or os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('MAIL_USERNAME') or os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('MAIL_PASSWORD') or os.getenv('SMTP_PASSWORD')

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

# Initialize MongoDB
init_mongodb()

@app.template_filter('format_datetime')
def format_datetime(value, format='%d %b %Y, %I:%M %p'):
    return value.strftime(format) if isinstance(value, datetime) else value

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
    app.logger.error(f"❌ SMTP import failed: {e}")

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
@app.route('/contact')
def contact():
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
    if mongo_db is None:
        return render_template('blog.html', posts=[])
    posts = list(mongo_db.blog_posts.find({'status': 'published'}).sort('published_date', -1))
    return render_template('blog.html', posts=posts)

@app.route('/blog/<slug>')
def blog_post(slug):
    """Display single blog post"""
    if mongo_db is None:
        return render_template('blog_single.html', post=None, related_posts=[]), 404
        
    post = mongo_db.blog_posts.find_one({'slug': slug, 'status': 'published'})
    
    related_posts = []
    if post:
        # Convert ObjectId to string for template
        post['id'] = str(post['_id'])

        if post.get('tags'):
            tags = post['tags'].split(',')
            related_posts = list(mongo_db.blog_posts.find({
                'status': 'published', '_id': {'$ne': post['_id']}, 'tags': {'$regex': tags[0].strip(), '$options': 'i'}
            }).limit(3))
        
        if not related_posts:
            related_posts = list(mongo_db.blog_posts.find({
                'status': 'published', '_id': {'$ne': post['_id']}
            }).sort('published_date', -1).limit(3))
    
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
            to_email = SMTP_USERNAME # Always send to admin
            # This block is for the homepage contact form, which is now deprecated.
            # We will keep the logic but it should not be used.
            # The new contact page uses /contact-submission
            # The renewal form uses this endpoint but with a form post.
            name = data.get('name')
            from_email = data.get('email')
            subject = data.get('subject')
            message = data.get('message')
            files = {}
            is_form_submission = False
        else:
            app.logger.info("Processing FORM request")
            to_email = SMTP_USERNAME # Always send to admin for renewal form
            name = request.form.get('name')
            from_email = request.form.get('email')
            subject = request.form.get('subject')
            message = request.form.get('message')
            files = request.files
            
            # Check if this is a renewal form submission
            is_form_submission = 'insuranceType' in request.form
            app.logger.info(f"Is renewal form submission (from /renewal): {is_form_submission}")
            app.logger.info(f"Form keys: {list(request.form.keys())}")

        app.logger.info(
            f"Required fields check - to: {bool(to_email)}, name: {bool(name)}, from: {bool(from_email)}, subject: {bool(subject)}, message: {bool(message)}")

        # Validate required fields
        if not all([to_email, name, from_email, subject, message]):
            app.logger.error(
                f"Missing required fields - to: {to_email}, name: {name}, email: {from_email}, subject: {subject}, message: {message}")
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
                age = request.form.get('age', type=int)  # Get age as integer
                date_of_birth = request.form.get('dateOfBirth', '')
                aadhaar = request.form.get('aadhaar', '')

                # Handle file uploads
                file_paths = {}
                file_fields = ['vehicleRC', 'previousPolicyMotor', 'previousPolicyHealth', 'previousPolicyShopkeeper', 'previousPolicyOthers']
                for field in file_fields:
                    if field in files:
                        file = files[field]
                        if file and allowed_file(file.filename):
                            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                            # Ensure upload folder exists
                            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                                os.makedirs(app.config['UPLOAD_FOLDER'])
                            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            file.save(file_path)
                            file_paths[field + '_file'] = filename # e.g., vehicleRC_file

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

                app.logger.info(
                    f"Form data extracted - Name: {first_name} {last_name}, Insurance: {insurance_type}")

                # Save to database
                if mongo_db is not None:
                    try:
                        app.logger.info("Attempting database insert...")
                        submission_data = {
                            'first_name': first_name, 'last_name': last_name, 'phone': phone, 'email': email, 'want_to': want_to,
                            'insurance_type': insurance_type, 'age': age, 'date_of_birth': date_of_birth, 'aadhaar': aadhaar,
                            'vehicle_rc': vehicle_rc, 'previous_policy_motor': previous_policy_motor,
                            'previous_policy_health': previous_policy_health, 'pre_existing_disease': pre_existing_disease,
                            'travel_country': travel_country, 'travel_duration': travel_duration, 'travel_age': travel_age,
                            'commodity_type': commodity_type, 'transport_mode': transport_mode, 'pre_carrying_unit': pre_carrying_unit,
                            'business_nature': business_nature, 'previous_policy_shopkeeper': previous_policy_shopkeeper,
                            'claim_occurred': claim_occurred, 'number_of_members': number_of_members, 'salary': salary,
                            'work_nature': work_nature, 'sum_insured': sum_insured, 'locality': locality, 'pincode': pincode,
                            'occupancy': occupancy, 'type_of_insurance': type_of_insurance, 'previous_policy_others': previous_policy_others,
                            'submission_date': datetime.now().isoformat(), 'status': 'new'
                        }

                        # Add file paths to the submission data
                        if file_paths:
                            submission_data.update(file_paths)

                        mongo_db.form_submissions.insert_one(submission_data)
                        app.logger.info("Database insert successful for renewal form.")
                    except Exception as db_error:
                        app.logger.error(f"Database error: {db_error}")
                        raise db_error

                # Send admin notification email
                try:
                    admin_msg = MIMEMultipart()
                    admin_msg['From'] = SMTP_USERNAME
                    admin_msg['To'] = SMTP_USERNAME
                    admin_msg['Subject'] = f"New Renewal Form Submission - {insurance_type}"

                    admin_body = f"""New renewal form submission received:

Name: {first_name} {last_name}
Email: {email}
Phone: {phone}
Age: {age}
Insurance Type: {insurance_type}
Aadhaar: {aadhaar}

Submission Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                    admin_msg.attach(MIMEText(admin_body, 'plain'))

                    try:
                        if not SMTP_USERNAME or not SMTP_PASSWORD:
                            raise ValueError("SMTP credentials are not configured in environment variables.")
                        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
                        server.starttls()
                        server.login(SMTP_USERNAME, SMTP_PASSWORD)
                        server.sendmail(SMTP_USERNAME, SMTP_USERNAME, admin_msg.as_string())
                        server.quit()
                        app.logger.info("Admin notification sent successfully")
                    except Exception as email_error_inner:
                        app.logger.error(f"Admin notification failed to send: {email_error_inner}")
                    # Don't fail the whole request if email fails

                except Exception as email_setup_error:
                    app.logger.error(f"Failed to prepare admin notification email: {email_setup_error}")

            except Exception as form_error:
                app.logger.error(f"Form processing error: {form_error}")
                # Optionally, rollback the transaction
                # conn.rollback()
                # Re-raise the exception to be caught by the outer try-except block
                raise form_error

        # This endpoint is now primarily for the renewal form.
        # The homepage contact form was removed, and the contact page uses /contact-submission
        if is_form_submission:
            return jsonify({"message": "Renewal form submitted successfully! Our team will contact you shortly."}), 200
        else:
            # This is for the old homepage form, which is no longer in use.
            return jsonify({"message": "Request received."}), 200

    except Exception as e:
        app.logger.error(f"CRITICAL ERROR in send_email: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Admin Routes
@app.route('/admin')
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            session.permanent = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    if mongo_db is None:
        flash("Database not configured. Dashboard data is unavailable.", "danger")
        return render_template('admin/dashboard.html', stats={}, recent_submissions=[], tasks=[], monthly_trends=[], submissions_by_type=[])

    try:
        # Fetch stats
        form_total = mongo_db.form_submissions.count_documents({})
        form_new = mongo_db.form_submissions.count_documents({'status': 'new'})
        contact_total = mongo_db.contact_submissions.count_documents({})
        contact_new = mongo_db.contact_submissions.count_documents({'status': 'new'})

        # Fetch recent activities
        recent_form_submissions = list(mongo_db.form_submissions.find().sort('submission_date', -1).limit(5))
        recent_contact_submissions = list(mongo_db.contact_submissions.find().sort('submission_date', -1).limit(5))
        
        # Fetch pending tasks
        pending_tasks = list(mongo_db.tasks.find({'status': 'pending'}).sort('due_date', 1).limit(5))

        # Convert ObjectIds to strings for templates
        for sub in recent_form_submissions: sub['id'] = str(sub['_id'])
        for sub in recent_contact_submissions: sub['id'] = str(sub['_id'])
        for task in pending_tasks: task['id'] = str(task['_id'])

        stats = {
            'form_total': form_total,
            'form_new': form_new,
            'contact_total': contact_total,
            'contact_new': contact_new,
        }

        # Fetch data for charts
        # Monthly trends
        monthly_trends_pipeline = [
            {'$project': {'month': {'$substr': ['$submission_date', 0, 7]}}},
            {'$group': {'_id': '$month', 'count': {'$sum': 1}}},
            {'$sort': {'_id': -1}},
            {'$limit': 6}
        ]
        monthly_trends = list(mongo_db.form_submissions.aggregate(monthly_trends_pipeline))
        # The template expects 'month' key, so let's rename '_id'
        for trend in monthly_trends:
            trend['month'] = trend.pop('_id')

        # Submissions by type
        submissions_by_type_pipeline = [
            {'$match': {'insurance_type': {'$ne': None, '$ne': ''}}},
            {'$group': {'_id': '$insurance_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        submissions_by_type = list(mongo_db.form_submissions.aggregate(submissions_by_type_pipeline))
        # The template expects 'insurance_type' key
        for sub_type in submissions_by_type:
            sub_type['insurance_type'] = sub_type.pop('_id')

    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        flash("Could not load all dashboard data due to a database error.", "danger")
        stats, recent_form_submissions, recent_contact_submissions, pending_tasks, monthly_trends, submissions_by_type = {}, [], [], [], [], []

    return render_template('admin/dashboard.html', stats=stats, recent_submissions=recent_form_submissions, 
                           tasks=pending_tasks, monthly_trends=monthly_trends, submissions_by_type=submissions_by_type)

@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        # Check if the email matches the admin email from .env file
        if email == ADMIN_EMAIL:
            try:
                token = s.dumps(email, salt='password-reset-salt')
                msg = Message('Password Reset Request', recipients=[email])
                link = url_for('reset_password', token=token, _external=True)
                msg.body = f'Your link to reset your password is {link}'
                mail.send(msg)
                flash('A password reset link has been sent to your email.', 'success')
                return redirect(url_for('admin_login'))
            except Exception as e:
                logger.error(f"Error sending password reset email: {e}")
                flash('Failed to send password reset email. Please try again.', 'danger')
        else:
            flash('Email address not found.', 'danger')
    return render_template('admin/forgot_password.html')

@app.route('/admin/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    global ADMIN_PASSWORD_HASH
    
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash('The password reset link has expired.', 'danger')
        return redirect(url_for('forgot_password'))
    except:
        flash('The password reset link is invalid.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('admin/reset_password.html', token=token)

        # Generate new password hash
        new_password_hash = generate_password_hash(password)
        
        # Update .env file with new password hash
        if update_env_file('ADMIN_PASSWORD_HASH', new_password_hash):
            # Reload environment variables
            load_dotenv(override=True)
            # Update global variable
            ADMIN_PASSWORD_HASH = new_password_hash
            flash('Your password has been updated successfully.', 'success')
            logger.info("Password reset successful and saved to .env file")
        else:
            flash('Password was updated temporarily, but failed to save to .env file. Please contact administrator.', 'warning')
            # Still update the global variable so it works until server restart
            ADMIN_PASSWORD_HASH = new_password_hash
        
        return redirect(url_for('admin_login'))

    return render_template('admin/reset_password.html', token=token)


@app.route('/admin/renewals')
@admin_required
def admin_renewals():
    return redirect(url_for('admin_submissions', want_to='renewal'))

@app.route('/admin/submissions')
@admin_required
def admin_submissions():
    if mongo_db is None:
        flash("Database not configured.", "danger")
        return render_template('admin/submissions.html', submissions=[], stats={}, total_pages=1, current_page=1, filters={})

    try:
        page = request.args.get('page', 1, type=int)
        PER_PAGE = 15
        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        insurance_type_filter = request.args.get('insurance_type', '')
        want_to_filter = request.args.get('want_to', '')

        query_filters = {}
        if status_filter:
            query_filters['status'] = status_filter
        if insurance_type_filter:
            query_filters['insurance_type'] = insurance_type_filter
        if want_to_filter:
            query_filters['want_to'] = want_to_filter
        
        if search_query:
            search_regex = {'$regex': search_query, '$options': 'i'}
            query_filters['$or'] = [
                {'first_name': search_regex},
                {'last_name': search_regex},
                {'email': search_regex},
                {'phone': search_regex},
            ]

        total_submissions = mongo_db.form_submissions.count_documents(query_filters)
        total_pages = (total_submissions + PER_PAGE - 1) // PER_PAGE
        
        submissions = list(mongo_db.form_submissions.find(query_filters)
                           .sort('submission_date', -1)
                           .skip((page - 1) * PER_PAGE)
                           .limit(PER_PAGE))
        
        for sub in submissions:
            sub['id'] = str(sub['_id'])

        stats = {
            'total': mongo_db.form_submissions.count_documents({}),
            'new': mongo_db.form_submissions.count_documents({'status': 'new'}),
            'processing': mongo_db.form_submissions.count_documents({'status': 'processing'}),
            'completed': mongo_db.form_submissions.count_documents({'status': 'completed'}),
        }
        return render_template('admin/submissions.html', submissions=submissions, stats=stats, total_pages=total_pages, current_page=page, filters={'search': search_query, 'status': status_filter, 'insurance_type': insurance_type_filter, 'want_to': want_to_filter})
    except Exception as e:
        logger.error(f"Error fetching submissions: {e}")
        flash("An error occurred while fetching submissions.", "danger")
        return render_template('admin/submissions.html', submissions=[], stats={}, total_pages=1, current_page=1, filters={})


@app.route('/admin/submission/<submission_id>')
@admin_required
def admin_submission_detail(submission_id):
    if mongo_db is None:
        flash("Database not configured.", "danger")
        return redirect(url_for('admin_dashboard'))
    
    try:
        submission = mongo_db.form_submissions.find_one({'_id': ObjectId(submission_id)})
        if not submission:
            flash("Submission not found.", "danger")
            return redirect(url_for('admin_submissions'))
        
        submission['id'] = str(submission['_id'])
        tasks = list(mongo_db.tasks.find({'submission_id': submission['id']}))
        for task in tasks:
            task['id'] = str(task['_id'])

        return render_template('admin/submission_detail.html', submission=submission, tasks=tasks)
    except Exception as e:
        logger.error(f"Error fetching submission detail: {e}")
        flash("An error occurred while fetching submission details.", "danger")
        return redirect(url_for('admin_submissions'))

@app.route('/admin/submissions/<submission_id>/update', methods=['POST'])
@admin_required
def admin_submission_update(submission_id):
    """Update the status and notes of a form submission."""
    if mongo_db is None:
        return jsonify({"error": "MongoDB not configured"}), 500
    
    try:
        data = request.get_json()
        status = data.get('status')
        notes = data.get('notes')
        user = session.get('admin_username', 'Admin')
        timestamp = datetime.now()

        update_data = {
            'status': status,
            'notes': notes,
            'processed_date': timestamp.isoformat(),
            'processed_by': user
        }
        
        history_entry = {
            'status': status, 'notes': notes, 'user': user, 'timestamp': timestamp
        }

        result = mongo_db.form_submissions.update_one({'_id': ObjectId(submission_id)}, {'$set': update_data, '$push': {'history': history_entry}})
        if result.matched_count == 0:
            return jsonify({"success": False, "message": "Submission not found"}), 404
        return jsonify({"success": True, "message": "Submission updated successfully"})
    except Exception as e:
        logger.error(f"Error updating submission {submission_id}: {e}")
        return jsonify({"success": False, "message": "An internal error occurred"}), 500

@app.route('/admin/contact-submissions')
@admin_required
def admin_contact_submissions():
    if mongo_db is None:
        flash("Database not configured.", "danger")
        return render_template('admin/contact_submissions.html', submissions=[], stats={}, total_pages=1, current_page=1, filters={})
    
    # Pagination and Filtering from request arguments
    page = request.args.get('page', 1, type=int)
    PER_PAGE = 15
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')

    query_filters = {}
    if status_filter:
        query_filters['status'] = status_filter
    
    if search_query:
        search_regex = {'$regex': search_query, '$options': 'i'}
        query_filters['$or'] = [
            {'first_name': search_regex},
            {'last_name': search_regex},
            {'email': search_regex},
            {'phone': search_regex},
        ]

    # Fetch submissions with filtering and pagination
    total_submissions = mongo_db.contact_submissions.count_documents(query_filters)
    total_pages = (total_submissions + PER_PAGE - 1) // PER_PAGE
    
    submissions = list(mongo_db.contact_submissions.find(query_filters)
                       .sort('submission_date', -1)
                       .skip((page - 1) * PER_PAGE)
                       .limit(PER_PAGE))
    
    for sub in submissions:
        sub['id'] = str(sub['_id'])

    # Fetch stats for the cards (these are global, not affected by filters)
    stats = {
        'total': mongo_db.contact_submissions.count_documents({}),
        'new': mongo_db.contact_submissions.count_documents({'status': 'new'}),
        'processing': mongo_db.contact_submissions.count_documents({'status': 'processing'}),
        'completed': mongo_db.contact_submissions.count_documents({'status': 'completed'}),
    }

    return render_template('admin/contact_submissions.html', submissions=submissions, stats=stats, total_pages=total_pages, current_page=page, filters={'search': search_query, 'status': status_filter})

@app.route('/admin/contact-submissions/<submission_id>/update', methods=['POST'])
@admin_required
def admin_contact_submission_update(submission_id):
    if mongo_db is None:
        return jsonify({"error": "MongoDB not configured"}), 500
    try:
        data = request.get_json()
        new_status = data.get('status')
        if not new_status:
            return jsonify({"error": "Status is required"}), 400
        
        result = mongo_db.contact_submissions.update_one(
            {'_id': ObjectId(submission_id)},
            {'$set': {'status': new_status, 'processed_date': datetime.now().isoformat()}}
        )
        if result.matched_count == 0:
            return jsonify({"error": "Submission not found"}), 404
        
        return jsonify({"success": True, "message": "Status updated"}), 200
    except Exception as e:
        app.logger.error(f"Error updating contact submission {submission_id}: {e}")
        return jsonify({"error": "Failed to update submission"}), 500

@app.route('/admin/contact-submissions/<submission_id>/delete', methods=['POST'])
@admin_required
def admin_contact_submission_delete(submission_id):
    """Delete a contact submission by id."""
    if mongo_db is None:
        return jsonify({"error": "MongoDB not configured"}), 500

    try:
        result = mongo_db.contact_submissions.delete_one({'_id': ObjectId(submission_id)})

        if result.deleted_count == 0:
            logger.warning(f"Contact submission not found for deletion: {submission_id}")
            return jsonify({"error": "Submission not found"}), 404
        
        logger.info(f"Deleted contact submission {submission_id} from MongoDB")
        return jsonify({"success": True, "message": "Submission deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting contact submission {submission_id}: {e}")
        return jsonify({"error": "Failed to delete submission"}), 500

@app.route('/admin/export_contact_submissions')
@admin_required
def admin_export_contact_submissions():
    """Exports filtered contact submissions to a CSV file."""
    if mongo_db is None:
        flash("Database not configured.", "danger")
        return redirect(url_for('admin_contact_submissions'))

    try:
        # Re-use filtering logic from the contact submissions page
        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', '')

        query_filters = {}
        if status_filter:
            query_filters['status'] = status_filter
        
        if search_query:
            search_regex = {'$regex': search_query, '$options': 'i'}
            query_filters['$or'] = [
                {'first_name': search_regex},
                {'last_name': search_regex},
                {'email': search_regex},
                {'phone': search_regex},
            ]

        # Fetch all matching submissions (no pagination)
        submissions = mongo_db.contact_submissions.find(query_filters).sort('submission_date', -1)

        # Generate CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        headers = ['ID', 'FirstName', 'LastName', 'Email', 'Phone', 'ActionRequested', 'InsuranceType', 'Status', 'SubmissionDate']
        writer.writerow(headers)

        # Write data rows
        for sub in submissions:
            writer.writerow([str(sub.get('_id')), sub.get('first_name'), sub.get('last_name'), sub.get('email'), sub.get('phone'), sub.get('action'), sub.get('insurance_type'), sub.get('status'), sub.get('submission_date')])

        output.seek(0)
        return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=contact_inquiries.csv"})
    except Exception as e:
        logger.error(f"Error exporting contact submissions: {e}")
        flash("An error occurred while exporting data.", "danger")
        return redirect(url_for('admin_contact_submissions'))

@app.route('/admin/export_submissions')
@admin_required
def admin_export_submissions():
    """Exports filtered form submissions to a CSV file."""
    if mongo_db is None:
        flash("Database not configured.", "danger")
        return redirect(url_for('admin_submissions'))

    try:
        # Re-use the same filtering logic from the submissions page
        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        insurance_type_filter = request.args.get('insurance_type', '')

        query_filters = {}
        if status_filter:
            query_filters['status'] = status_filter
        if insurance_type_filter:
            query_filters['insurance_type'] = insurance_type_filter
        
        if search_query:
            search_regex = {'$regex': search_query, '$options': 'i'}
            query_filters['$or'] = [
                {'first_name': search_regex},
                {'last_name': search_regex},
                {'email': search_regex},
                {'phone': search_regex},
            ]

        # Fetch all matching submissions (no pagination)
        submissions = mongo_db.form_submissions.find(query_filters).sort('submission_date', -1)

        # Generate CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        headers = ['ID', 'FirstName', 'LastName', 'Email', 'Phone', 'DOB', 'Aadhaar', 'InsuranceType', 'Status', 'SubmissionDate', 'Notes']
        writer.writerow(headers)

        # Write data rows
        for sub in submissions:
            writer.writerow([str(sub.get('_id')), sub.get('first_name'), sub.get('last_name'), sub.get('email'), sub.get('phone'), sub.get('date_of_birth'), sub.get('aadhaar'), sub.get('insurance_type'), sub.get('status'), sub.get('submission_date'), sub.get('notes')])

        output.seek(0)
        return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=form_submissions.csv"})
    except Exception as e:
        logger.error(f"Error exporting submissions: {e}")
        flash("An error occurred while exporting data.", "danger")
        return redirect(url_for('admin_submissions'))

@app.route('/admin/submission/<submission_id>/delete', methods=['POST'])
@admin_required
def admin_form_submission_delete(submission_id):
    """Delete a form submission by id."""
    if mongo_db is None:
        return jsonify({"error": "MongoDB not configured"}), 500

    try:
        result = mongo_db.form_submissions.delete_one({'_id': ObjectId(submission_id)})

        if result.deleted_count == 0:
            logger.warning(f"Form submission not found for deletion: {submission_id}")
            return jsonify({"error": "Submission not found"}), 404
        
        logger.info(f"Deleted form submission {submission_id} from MongoDB")
        return jsonify({"success": True, "message": "Submission deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting form submission {submission_id}: {e}")
        return jsonify({"error": "Failed to delete submission"}), 500

@app.route('/admin/blog')
@admin_required
def admin_blog():
    """Admin page for managing blog posts with pagination, filters, and sorting."""
    if mongo_db is None:
        flash("Database not configured.", "danger")
        return render_template('admin/blog.html', posts=[], total_count=0, total_pages=1, current_page=1, status_filter='', search_query='', sort_by='created_date', sort_order='desc')

    try:
        page = request.args.get('page', 1, type=int)
        PER_PAGE = 15 # Number of posts per page
        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        # New sorting parameters
        sort_by = request.args.get('sort_by', 'created_date') # Default sort by created_date
        sort_order_str = request.args.get('sort_order', 'desc') # Default sort order descending

        # Convert sort_order_str to pymongo sort order
        if sort_order_str == 'asc':
            sort_order = pymongo.ASCENDING
        else:
            sort_order = pymongo.DESCENDING # Default to descending

        query_filters = {}
        if status_filter:
            query_filters['status'] = status_filter
        
        if search_query:
            search_regex = {'$regex': search_query, '$options': 'i'}
            query_filters['$or'] = [
                {'title': search_regex},
                {'content': search_regex},
                {'author': search_regex},
                {'tags': search_regex}
            ]

        total_posts = mongo_db.blog_posts.count_documents(query_filters)
        published_posts_count = mongo_db.blog_posts.count_documents({'status': 'published'})
        draft_posts_count = mongo_db.blog_posts.count_documents({'status': 'draft'})
        archived_posts_count = mongo_db.blog_posts.count_documents({'status': 'archived'})

        total_pages = (total_posts + PER_PAGE - 1) // PER_PAGE
        
        # Ensure current_page is within valid range
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
        elif total_pages == 0:
            page = 1

        posts = list(mongo_db.blog_posts.find(query_filters)
                           .sort(sort_by, sort_order) # Apply dynamic sorting
                           .skip((page - 1) * PER_PAGE)
                           .limit(PER_PAGE))
        
        for post in posts:
            post['id'] = str(post['_id'])

        return render_template('admin/blog.html', 
                               posts=posts, 
                               total_count=total_posts,
                               published_posts_count=published_posts_count,
                               draft_posts_count=draft_posts_count,
                               archived_posts_count=archived_posts_count,
                               total_pages=total_pages, 
                               current_page=page, 
                               status_filter=status_filter,
                               search_query=search_query,
                               sort_by=sort_by,           # Pass sort_by to template
                               sort_order=sort_order_str, # Pass sort_order_str to template
                               request=request) 
    except Exception as e:
        logger.error(f"Error fetching blog posts for admin panel: {e}")
        flash("An error occurred while fetching blog posts.", "danger")
        return render_template('admin/blog.html', posts=[], total_count=0, published_posts_count=0, draft_posts_count=0, archived_posts_count=0, total_pages=1, current_page=1, status_filter='', search_query='', sort_by='created_date', sort_order='desc')

@app.route('/admin/blog/new', methods=['GET', 'POST'])
@admin_required
def admin_blog_new():
    """Create a new blog post."""
    if mongo_db is None:
        flash("Database not configured.", "danger")
        return redirect(url_for('admin_blog'))

    if request.method == 'POST':
        try:
            post_data = {
                "title": request.form.get('title'),
                "slug": request.form.get('slug'),
                "content": request.form.get('content'),
                "excerpt": request.form.get('excerpt'),
                "author": request.form.get('author', 'Bima With Bali'),
                "status": request.form.get('status', 'draft'),
                "tags": request.form.get('tags'),
                "featured_image": request.form.get('featured_image'),
                "meta_description": request.form.get('meta_description'),
                "created_date": datetime.now(),
                "updated_date": datetime.now(),
                "published_date": datetime.now() if request.form.get('status') == 'published' else None
            }
            mongo_db.blog_posts.insert_one(post_data)
            flash('Blog post created successfully!', 'success')
            return redirect(url_for('admin_blog'))
        except Exception as e:
            logger.error(f"Error creating blog post: {e}")
            flash(f"An error occurred: {e}", 'danger')

    return render_template('admin/blog_form.html', post=None, title="Create New Post")

@app.route('/admin/blog/<string:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_blog_edit(post_id):
    """Edit an existing blog post."""
    if mongo_db is None:
        flash("Database not configured.", "danger")
        return redirect(url_for('admin_blog'))

    post = mongo_db.blog_posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        flash('Blog post not found.', 'danger')
        return redirect(url_for('admin_blog'))

    if request.method == 'POST':
        try:
            updated_data = {
                "title": request.form.get('title'),
                "slug": request.form.get('slug'),
                "content": request.form.get('content'),
                "excerpt": request.form.get('excerpt'),
                "author": request.form.get('author', 'Bima With Bali'),
                "status": request.form.get('status', 'draft'),
                "tags": request.form.get('tags'),
                "featured_image": request.form.get('featured_image'),
                "meta_description": request.form.get('meta_description'),
                "updated_date": datetime.now(),
            }
            # Update published_date only if status changes to 'published' and it wasn't published before
            if post.get('status') != 'published' and updated_data['status'] == 'published':
                updated_data['published_date'] = datetime.now()
            elif updated_data['status'] != 'published':
                updated_data['published_date'] = None # Clear published date if not published

            mongo_db.blog_posts.update_one({'_id': ObjectId(post_id)}, {'$set': updated_data})
            flash('Blog post updated successfully!', 'success')
            return redirect(url_for('admin_blog'))
        except Exception as e:
            logger.error(f"Error updating blog post {post_id}: {e}")
            flash(f"An error occurred: {e}", 'danger')

    # Convert ObjectId to string for template
    post['id'] = str(post['_id'])
    return render_template('admin/blog_form.html', post=post, title="Edit Post")

@app.route('/admin/blog/<string:post_id>/delete', methods=['POST'])
@admin_required
def admin_blog_delete(post_id):
    """Delete a blog post."""
    if mongo_db is None:
        return jsonify({"success": False, "message": "Database not configured."}), 500
    try:
        result = mongo_db.blog_posts.delete_one({'_id': ObjectId(post_id)})
        if result.deleted_count == 1:
            return jsonify({"success": True, "message": "Blog post deleted successfully."}), 200
        else:
            return jsonify({"success": False, "message": "Blog post not found."}), 404
    except Exception as e:
        logger.error(f"Error deleting blog post {post_id}: {e}")
        return jsonify({"success": False, "message": "An error occurred while deleting the post."}), 500

@app.route('/admin/blog/<string:post_id>/status', methods=['POST'])
@admin_required
def admin_blog_status(post_id):
    """Update the status of a blog post."""
    if mongo_db is None:
        return jsonify({"success": False, "message": "Database not configured."}), 500
    try:
        data = request.get_json()
        new_status = data.get('status')
        if new_status not in ['draft', 'published', 'archived']:
            return jsonify({"success": False, "message": "Invalid status provided."}), 400

        update_data = {
            "status": new_status,
            "updated_date": datetime.now()
        }
        # Update published_date if status changes to 'published', otherwise clear it
        if new_status == 'published':
            update_data['published_date'] = datetime.now()
        else:
            update_data['published_date'] = None 

        result = mongo_db.blog_posts.update_one({'_id': ObjectId(post_id)}, {'$set': update_data})
        if result.matched_count == 1:
            return jsonify({"success": True, "message": f"Blog post status updated to {new_status}."}), 200
        else:
            return jsonify({"success": False, "message": "Blog post not found."}), 404
    except Exception as e:
        logger.error(f"Error updating status for blog post {post_id}: {e}")
        return jsonify({"success": False, "message": "An error occurred while updating the post status."}), 500


POLICY_PROVIDERS = [
    "Acko General Insurance", "Aditya Birla Health Insurance", "Bajaj Allianz General Insurance",
    "Bharti AXA General Insurance", "Care Health Insurance", "Cholamandalam MS General Insurance",
    "Digit General Insurance", "Edelweiss General Insurance", "Future Generali India Insurance",
    "HDFC ERGO General Insurance", "ICICI Lombard General Insurance", "IFFCO Tokio General Insurance",
    "Kotak Mahindra General Insurance", "Liberty General Insurance", "Magma HDI General Insurance",
    "National Insurance Company", "Navi General Insurance", "New India Assurance",
    "Niva Bupa Health Insurance", "Oriental Insurance Company", "Raheja QBE General Insurance",
    "Reliance General Insurance", "Royal Sundaram General Insurance", "SBI General Insurance",
    "Shriram General Insurance", "Star Health & Allied Insurance", "Tata AIG General Insurance",
    "United India Insurance", "Universal Sompo General Insurance", "Zuno General Insurance",
    "Other"
]

@app.route('/admin/quotes/new', methods=['GET', 'POST'])
@admin_required
def admin_quotes_new():
    """Page to create a new quote, optionally based on a submission."""
    submission_id = request.args.get('submission_id')
    submission = None
    if submission_id and mongo_db is not None:
        try:
            submission = mongo_db.form_submissions.find_one({'_id': ObjectId(submission_id)})
            if submission:
                submission['id'] = str(submission['_id'])
        except Exception as e:
            logger.error(f"Error fetching submission for new quote: {e}")
            flash("Could not load submission data for the quote.", "danger")

    if request.method == 'POST':
        try:
            # 1. Get Form Data
            quote_data = {
                "customer_name": request.form.get('customerName'),
                "customer_email": request.form.get('customerEmail'),
                "insurance_type": request.form.get('insuranceType'),
                "policy_provider": request.form.get('policyProvider'),
                "policy_details": request.form.get('policyDetails'),
                "base_premium": float(request.form.get('basePremium')),
                "gst": float(request.form.get('gst')),
                "total_premium": float(request.form.get('totalPremium')),
                "submission_id": submission_id,
                "created_date": datetime.now()
            }

            # 2. Save Quote to Database
            if mongo_db is not None:
                mongo_db.quotes.insert_one(quote_data)
                logger.info("Quote saved to database.")
            else:
                flash("Database not configured. Quote not saved.", "warning")

            # 3. Send Email to Customer
            customer_email = quote_data["customer_email"]
            if customer_email:
                msg = MIMEMultipart()
                msg['From'] = SMTP_USERNAME
                msg['To'] = customer_email
                msg['Subject'] = f"Your Insurance Quote from Bima with Bali"

                body = f"""
<html>
<head></head>
<body>
    <p>Dear {quote_data['customer_name']},</p>
    <p>Thank you for your interest. Here is your insurance quote:</p>
    <p>
        <b>Insurance Type:</b> {quote_data['insurance_type']}<br>
        <b>Provider:</b> {quote_data['policy_provider']}
    </p>
    <h3>Pricing:</h3>
    <p>
        <b>Base Premium:</b> ₹{quote_data['base_premium']:.2f}<br>
        <b>GST:</b> {quote_data['gst']}%<br>
        <b>Total Premium:</b> ₹{quote_data['total_premium']:.2f}
    </p>
    <h3>Policy Details:</h3>
    <p>{quote_data['policy_details']}</p>
    <p>If you have any questions or wish to proceed, please contact us.</p>
    <p>Best regards,<br>The Bima with Bali Team</p>
</body>
</html>
"""
                msg.attach(MIMEText(body, 'html'))

                try:
                    logger.info(f"Preparing to send quote email to {customer_email} from {SMTP_USERNAME}")
                    if not SMTP_USERNAME or not SMTP_PASSWORD:
                        raise ValueError("SMTP credentials are not configured in environment variables.")
                    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
                    logger.info("SMTP server connected.")
                    server.starttls()
                    logger.info("TLS started.")
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                    logger.info("SMTP server logged in.")
                    server.sendmail(SMTP_USERNAME, customer_email, msg.as_string())
                    logger.info("Email sent.")
                    server.quit()
                    logger.info(f"Quote email sent to {customer_email}")
                    flash('Quote sent to customer successfully!', 'success')
                except Exception as email_error:
                    logger.error(f"Failed to send quote email: {email_error}", exc_info=True)
                    flash(f"Quote saved, but failed to send email. Please check the server logs for more details.", 'danger')
            else:
                flash("No customer email provided. Quote saved but not sent.", "warning")

            return redirect(url_for('admin_submissions'))

        except Exception as e:
            logger.error(f"Error processing new quote: {e}")
            flash(f"An error occurred while creating the quote: {e}", 'danger')

    logger.info(f"Rendering quote form with {len(POLICY_PROVIDERS)} providers.")
    return render_template('admin/quote_form.html', submission=submission, title="Create New Quote", providers=POLICY_PROVIDERS)

@app.route('/admin/api/submissions-over-time')
@admin_required
def admin_api_submissions_over_time():
    """API endpoint for submissions in the last N days."""
    if mongo_db is None:
        return jsonify({"error": "MongoDB not configured"}), 500

    try:
        days = request.args.get('days', 7, type=int)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        pipeline = [
            {'$match': {'submission_date': {'$gte': start_date.isoformat()}}},
            {'$project': {'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': {'$toDate': '$submission_date'}}}}},
            {'$group': {'_id': '$date', 'count': {'$sum': 1}}},
            {'$sort': {'_id': 1}}
        ]
        data = list(mongo_db.form_submissions.aggregate(pipeline))
        
        data_dict = {item['_id']: item['count'] for item in data}
        
        labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days + 1)]
        counts = [data_dict.get(label, 0) for label in labels]

        return jsonify({'labels': labels, 'data': counts})
    except Exception as e:
        logger.error(f"API submissions-over-time failed: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/admin/api/submissions-by-type')
@admin_required
def admin_api_submissions_by_type():
    """API endpoint to get submission counts grouped by insurance type for charts."""
    if mongo_db is None:
        return jsonify({"error": "MongoDB not configured"}), 500

    try:
        pipeline = [
            {'$match': {'insurance_type': {'$ne': None, '$ne': ''}}},
            {
                '$group': {
                    '_id': '$insurance_type',
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'count': -1}}
        ]
        data = list(mongo_db.form_submissions.aggregate(pipeline))

        labels = [item['_id'] for item in data]
        counts = [item['count'] for item in data]

        return jsonify({'labels': labels, 'data': counts})
    except Exception as e:
        logger.error(f"API submissions-by-type failed: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/admin/tasks/new', methods=['POST'])
@admin_required
def admin_create_task():
    if mongo_db is None:
        return jsonify({"error": "MongoDB not configured"}), 500
    try:
        data = request.get_json()
        submission_id = data.get('submission_id')
        description = data.get('description')
        due_date = data.get('due_date')

        if not all([submission_id, description, due_date]):
            return jsonify({'error': 'Missing required fields'}), 400

        task = {
            'submission_id': submission_id,
            'description': description,
            'due_date': datetime.fromisoformat(due_date),
            'status': 'pending',
            'created_at': datetime.now(),
            'assigned_to': session.get('username', 'Admin')
        }
        result = mongo_db.tasks.insert_one(task)
        task['_id'] = str(result.inserted_id)
        task['due_date'] = task['due_date'].isoformat() # for JSON serialization
        return jsonify({'success': True, 'task': task})
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({'error': 'Server error while creating task'}), 500

@app.route('/contact-submission', methods=['POST'])
def contact_submission():
    try:
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        phone = request.form.get('phone')
        email = request.form.get('email')
        action = request.form.get('action')
        insurance_type = request.form.get('insuranceType')

        if not all([first_name, last_name, phone, action, insurance_type]):
            return jsonify({"error": "Missing required fields"}), 400

        submission_data = {
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "email": email,
            "action": action,
            "insurance_type": insurance_type,
            "submission_date": datetime.now(),
            "status": "new"
        }

        if mongo_db is not None:
            mongo_db.contact_submissions.insert_one(submission_data)
            logger.info("Contact submission saved to MongoDB.")
        else:
            logger.error("MongoDB not configured for contact submission.")
            return jsonify({"error": "Database not configured"}), 500

        # Send admin notification email
        try:
            admin_email = SMTP_USERNAME
            admin_msg = MIMEMultipart()
            admin_msg['From'] = SMTP_USERNAME
            admin_msg['To'] = admin_email
            admin_msg['Subject'] = f"New Contact Form Inquiry: {insurance_type}"

            admin_body = f"""A new "Get in Touch" form was submitted on the contact page:

Name: {first_name} {last_name}
Email: {email}
Phone: {phone}
Insurance Type: {insurance_type}
Action Requested: {action}

Submission Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            admin_msg.attach(MIMEText(admin_body, 'plain'))

            try:
                if not SMTP_USERNAME or not SMTP_PASSWORD:
                    raise ValueError("SMTP credentials are not configured in environment variables.")
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SMTP_USERNAME, admin_email, admin_msg.as_string())
                server.quit()
                logger.info("Contact form admin notification sent successfully.")
            except Exception as email_error_inner:
                logger.error(f"Contact form admin notification failed to send: {email_error_inner}")
        except Exception as email_error:
            logger.error(f"Failed to prepare contact form admin notification: {email_error}")

        return jsonify({"message": "Form submitted successfully! Our team will contact you shortly."}), 200

    except Exception as e:
        logger.error(f"Error in /contact-submission: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handles chat messages and gets a response from the Groq AI."""
    # 1. Check if the Groq client is configured
    if not client:
        logger.error("Attempted to use /api/chat but Groq client is not configured.")
        return jsonify({"error": "AI service is not configured on the server."}), 503

    try:
        # 2. Get the user's message from the JSON request body
        data = request.get_json()
        messages = data.get('messages')

        if not messages:
            return jsonify({"error": "No messages provided in the request."}), 400

        # 3. Define a generator function to stream the response
        def generate_chunks():
            try:
                # Create a streaming chat completion request to Groq
                stream = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a friendly and professional AI assistant for 'Bima With Bali', an insurance services company named Bali. Your name is Bali.
Your primary goal is to answer user questions about the insurance products we offer.

The user has been shown this menu:
1: Motor Insurance, 2: Health Insurance, 3: Life & Term Insurance, 4: Fire & Property Insurance, 5: Shopkeeper Insurance, 6: Workmen/Employee Insurance, 7: Marine Insurance, 8: Travel Insurance, 9: Miscellaneous Insurance, 10: Claim Support, 0: Talk to Human Expert.

When a user selects a number, respond accordingly:
- If user selects 1 (Motor): First respond with ONLY: "Zaroor! Aap kaunsa motor insurance chahte hain?\n\nA) Car 🚘\nB) Bike 🏍️\nC) Commercial Vehicle 🚛". After they reply, ask for details with ONLY: "Please share:\n* Vehicle model\n* Registration year\n* Previous policy active? (Yes/No)".
- If user selects 2 (Health): Respond with ONLY: "Health insurance se medical bills ka stress zero 👍\n\nOptions:\nA) Individual\nB) Family Floater\nC) Senior Citizen\nD) Corporate / Group Mediclaim\n\nPlease share 👇\n\n* Age(s)\n* City\n* Any medical history? (Yes/No)".
- If user selects 3 (Life/Term): Respond with ONLY: "Family security is priority 💛\n\nPlease share:\n\n* Age\n* Income\n* Tobacco user? (Yes/No)".
- If user selects 4 (Fire/Property): Respond with ONLY: "Perfect — fire & property insurance assets ko secure karta hai 🔥 🏢\n\nPlease specify:\nA) Home\nB) Office\nC) Factory / Warehouse\nD) Commercial Property\n\nNeed details 👇\n\n* Property type\n* Location\n* Value / square ft area".
- If user selects 5 (Shopkeeper): Respond with ONLY: "Shop owners ke liye perfect protection 🏪💼\n\nShare details:\n\n* Business type\n* Shop area (sq ft)\n* Location".
- If user selects 6 (Workmen/Employee): Respond with ONLY: "Employee safety is company strength 🧑‍💼🛠️\n\nWhich cover?\nA) Workmen Compensation (WC)\nB) Employer Liability\nC) Group Personal Accident (GPA)\nD) ESIC/Employee Health cover\n\nRequired:\n\n* No. of employees\n* Nature of work\n* Salary details (approx)".
- If user selects 7 (Marine): Respond with ONLY: "Goods movement secure karna smart choice 🚚🚢✈️\n\nType choose karein:\nA) Inland Transit\nB) Import / Export\nC) Courier / Logistics Goods\n\nRequired details:\n\n* Goods type\n* Start & end location\n* Invoice value".
- If user selects 8 (Travel): Respond with ONLY: "Travel tension-free banate hain ✈️😇\n\nPlease share:\n\n* Travel destination\n* Duration\n* Age".
- If user selects 9 (Miscellaneous): Respond with ONLY: "Hum almost sab cover karte hain 😊\n\nOptions include:\n✅ Home Insurance\n✅ Office Insurance\n✅ Professional Indemnity\n✅ Public Liability\n✅ Cyber Insurance\n✅ Pet Insurance\n✅ Wedding / Event Cancellation\n✅ Burglary\n✅ Electronic Equipment\n✅ Credit / Surety Bonds\n✅ Many More\n\nWrite your requirement 👇".
- If user selects 10 (Claim Support): Respond with ONLY: "Claim processing support mil jayega 🤝\n\nShare:\n\n* Policy Type\n* Insurance Company\n* Claim Type\n* Your Phone Number\n\nOur expert team will call you 📞".
- If user selects 0 (Talk to Expert): Respond with ONLY: "Sure! Human expert aapko guide karega 📞\n\nPlease share:\n\n* Name\n* Phone Number".
- If the user gives a wrong or unclear input, respond with ONLY: "Oops 😅 Yeh option samajh nahi aaya.\nPlease reply with menu number (0–10) ya apna requirement type karein 💬".

General rules:
- Your name is Bali. You are a friendly and professional AI assistant for 'Bima With Bali'.
- Follow the instructions for menu selections exactly.
- Provide clear, helpful information. Do not invent policy details.
- Communicate directly and do not use special symbols like parentheses unless they are in the instructions.
- If you don't know an answer, advise the user that an expert will help.
- When ending a conversation, you can use a closing message like: "Thank you for trusting Bima With Bali 🤗 Humara mission hai — Insurance ko easy, simple & friendly banana. Have a secure day! 🌟 *Bima ho toh Bali ke saath!*".
"""
                        }
                    ] + messages, # Append the conversation history
                    model="llama-3.1-8b-instant",
                    stream=True,  # Enable streaming
                )
                # Yield each chunk of content as it arrives
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            except Exception as e:
                logger.error(f"Error during Groq stream generation: {e}")

        # 4. Return a streaming response
        return Response(generate_chunks(), mimetype='text/plain')
    except Exception as e:
        logger.error(f"Error in /api/chat: {e}")
        return jsonify({"error": "An internal error occurred while processing your message."}), 500

@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # The debug=True flag enables the debugger and reloader
    # This block must be at the end of the file
    app.run(debug=True, host='0.0.0.0', port=5000)