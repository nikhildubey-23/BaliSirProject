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
import sqlite3
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

# File extensions allowed
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'csv', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database configuration
DATABASE = os.getenv('DATABASE_URL', 'admin_panel.db')

# For production environments like Vercel, use /tmp/ for database
if os.environ.get('VERCEL') or os.environ.get('RAILWAY_ENVIRONMENT'):
    # Use temporary directory in production
    import tempfile
    temp_dir = tempfile.gettempdir()
    DATABASE = os.path.join(temp_dir, 'admin_panel.db')

# Configure Groq API safely
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize Groq client: {e}")
        client = None
else:
    client = None
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
    """Get database connection with error handling"""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize database with required tables"""
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Failed to connect to database")
            return False
        
        # Create form submissions table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS form_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                want_to TEXT,
                insurance_type TEXT NOT NULL,
                age INTEGER,
                date_of_birth TEXT,
                aadhaar TEXT,
                -- Motor fields
                vehicle_rc TEXT,
                previous_policy_motor TEXT,
                -- Health fields
                previous_policy_health TEXT,
                pre_existing_disease TEXT,
                -- Travel fields
                travel_country TEXT,
                travel_duration TEXT,
                travel_age TEXT,
                -- Marine fields
                commodity_type TEXT,
                transport_mode TEXT,
                pre_carrying_unit TEXT,
                -- Shopkeeper fields
                business_nature TEXT,
                previous_policy_shopkeeper TEXT,
                claim_occurred TEXT,
                -- Workmen fields
                number_of_members TEXT,
                salary TEXT,
                work_nature TEXT,
                -- Fire fields
                sum_insured TEXT,
                locality TEXT,
                pincode TEXT,
                occupancy TEXT,
                -- Others fields
                type_of_insurance TEXT,
                previous_policy_others TEXT,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new',
                notes TEXT,
                processed_by TEXT,
                processed_date TIMESTAMP
            )
        ''')
        
        # Create blog posts table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blog_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                excerpt TEXT,
                author TEXT DEFAULT 'Bima With Bali',
                status TEXT DEFAULT 'draft',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_date TIMESTAMP,
                featured_image TEXT,
                tags TEXT,
                meta_description TEXT
            )
        ''')
        

        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False

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
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT * FROM blog_posts
        WHERE status = 'published'
        ORDER BY published_date DESC, created_date DESC
    ''').fetchall()
    conn.close()
    return render_template('blog.html', posts=posts)

@app.route('/blog/<slug>')
def blog_post(slug):
    """Display single blog post"""
    conn = get_db_connection()
    post = conn.execute('''
        SELECT * FROM blog_posts
        WHERE slug = ? AND status = 'published'
    ''', (slug,)).fetchone()
    
    related_posts = []
    if post:
        if post['tags']:
            tags = post['tags'].split(',')
            related_posts = conn.execute('''
                SELECT * FROM blog_posts
                WHERE status = 'published'
                AND id != ?
                AND (tags LIKE ? OR tags LIKE ?)
                ORDER BY RANDOM()
                LIMIT 3
            ''', (post['id'], f'%{tags[0].strip()}%', f'%{tags[0].strip()}%')).fetchall()
        
        if not related_posts:
            related_posts = conn.execute('''
                SELECT * FROM blog_posts
                WHERE status = 'published'
                AND id != ?
                ORDER BY published_date DESC, created_date DESC
                LIMIT 3
            ''', (post['id'],)).fetchall()
    
    conn.close()
    
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
                conn = get_db_connection()
                if conn:
                    try:
                        app.logger.info("Attempting database insert...")
                        conn.execute('''
                            INSERT INTO form_submissions (
                                first_name, last_name, phone, email, want_to, insurance_type, age, date_of_birth, aadhaar,
                                vehicle_rc, previous_policy_motor, previous_policy_health, pre_existing_disease,
                                travel_country, travel_duration, travel_age, commodity_type, transport_mode, pre_carrying_unit,
                                business_nature, previous_policy_shopkeeper, claim_occurred, number_of_members, salary, work_nature,
                                sum_insured, locality, pincode, occupancy, type_of_insurance, previous_policy_others
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            first_name, last_name, phone, email, want_to, insurance_type, age, date_of_birth, aadhaar,
                            vehicle_rc, previous_policy_motor, previous_policy_health, pre_existing_disease,
                            travel_country, travel_duration, travel_age, commodity_type, transport_mode, pre_carrying_unit,
                            business_nature, previous_policy_shopkeeper, claim_occurred, number_of_members, salary, work_nature,
                            sum_insured, locality, pincode, occupancy, type_of_insurance, previous_policy_others
                        ))
                        conn.commit()
                        app.logger.info("Database insert successful")
                    except Exception as db_error:
                        app.logger.error(f"Database error: {db_error}")
                        # Optionally, rollback the transaction
                        # conn.rollback()
                        # Re-raise the exception to be caught by the outer try-except block
                        raise db_error
                    finally:
                        conn.close()

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
Age: {age}
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
                # Optionally, rollback the transaction
                # conn.rollback()
                # Re-raise the exception to be caught by the outer try-except block
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
                file_fields = ['vehicleRC', 'previousPolicyMotor', 'previousPolicyHealth', 'previousPolicyShopkeeper',
                               'previousPolicyOthers']
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
                                return jsonify(
                                    {"error": f"File {file.filename} has invalid extension. Only PDF and image files are allowed."}), 400

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
                return jsonify(
                    {"message": "Renewal form submitted successfully! Our team will contact you shortly."}), 200
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