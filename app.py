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

# Database configuration
DATABASE = os.getenv('DATABASE_URL', 'admin_panel.db')

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
                email TEXT NOT NULL,
                want_to TEXT NOT NULL,
                insurance_type TEXT NOT NULL,
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
        
        # Create admin sessions table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                admin_user TEXT NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT
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

def cleanup_audit_log():
    """Keep only the top 5 most recent audit log entries"""
    try:
        conn = get_db_connection()
        # Get the ID of the 5th most recent entry
        fifth_entry = conn.execute('''
            SELECT id FROM admin_sessions
            ORDER BY login_time DESC
            LIMIT 1 OFFSET 4
        ''').fetchone()
        
        if fifth_entry:
            # Delete all entries older than the 5th most recent
            conn.execute('''
                DELETE FROM admin_sessions
                WHERE id < ?
            ''', (fifth_entry['id'],))
            conn.commit()
        
        conn.close()
    except Exception as e:
        app.logger.error(f"Error cleaning up audit log: {e}")

# Initialize database on startup
init_db()

# Static files and favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/favicon.png')
def favicon_png():
    return send_from_directory('static', 'favicon.png', mimetype='image/png')

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
        # Save to database if this is a form submission (not admin email)
        if 'insuranceType' in request.form if not request.is_json else 'insuranceType' in data:
            # This is a contact form submission
            if not request.is_json:
                first_name = request.form.get('firstName', '')
                last_name = request.form.get('lastName', '')
                phone = request.form.get('phone', '')
                want_to = request.form.get('wantTo', '')
                insurance_type = request.form.get('insuranceType', '')
                
                conn = get_db_connection()
                if conn:
                    conn.execute('''
                        INSERT INTO form_submissions (first_name, last_name, phone, email, want_to, insurance_type)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (first_name, last_name, phone, from_email, want_to, insurance_type))
                    conn.commit()
                    conn.close()
                    
                    # Send notification email to admin (with error handling)
                    try:
                        admin_msg = MIMEMultipart()
                        admin_msg['From'] = SMTP_USERNAME
                        admin_msg['To'] = "sparksolutionfreelancing@gmail.com"
                        admin_msg['Subject'] = f"New Form Submission - {insurance_type}"
                        
                        admin_body = f"""
New form submission received:

Name: {first_name} {last_name}
Email: {from_email}
Phone: {phone}
Insurance Type: {insurance_type}
Request Type: {want_to}

Message: {message}

Submission Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        """
                        admin_msg.attach(MIMEText(admin_body, 'plain'))
                        
                        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                        server.starttls()
                        server.login(SMTP_USERNAME, SMTP_PASSWORD)
                        server.sendmail(SMTP_USERNAME, "sparksolutionfreelancing@gmail.com", admin_msg.as_string())
                        server.quit()
                        app.logger.info("Admin notification sent successfully")
                    except Exception as e:
                        app.logger.error(f"Error sending admin notification: {e}")
        
        # Try to send the main email
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
        except Exception as email_error:
            app.logger.error(f"Email sending failed: {email_error}")
            # If email fails but form was saved, still return success for form submission
            return jsonify({"message": "Form submitted successfully. Email delivery may be delayed."}), 200
            
    except Exception as e:
        app.logger.error(f"General error in send_email: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again later."}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    history = data.get('history', [])

    # Check if Groq client is available
    if client is None:
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
            logger.error(f"Groq API error: {e2}")
            response_text = "I'm sorry, but I'm having trouble connecting right now. Please try again later or contact our team directly for immediate assistance."

    return jsonify({'response': response_text})

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
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
            
            # Log admin session
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO admin_sessions (session_id, admin_user, ip_address, user_agent)
                VALUES (?, ?, ?, ?)
            ''', (session_id, username, request.remote_addr, request.headers.get('User-Agent')))
            conn.commit()
            conn.close()
            
            # Cleanup audit log to keep only top 5
            cleanup_audit_log()
            
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
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
    """Admin dashboard with key metrics"""
    conn = get_db_connection()
    
    # Get dashboard statistics
    total_submissions = conn.execute('SELECT COUNT(*) as count FROM form_submissions').fetchone()['count']
    new_submissions = conn.execute('SELECT COUNT(*) as count FROM form_submissions WHERE status = "new"').fetchone()['count']
    total_blog_posts = conn.execute('SELECT COUNT(*) as count FROM blog_posts').fetchone()['count']
    published_posts = conn.execute('SELECT COUNT(*) as count FROM blog_posts WHERE status = "published"').fetchone()['count']
    
    # Get recent submissions
    recent_submissions = conn.execute('''
        SELECT * FROM form_submissions
        ORDER BY submission_date DESC
        LIMIT 10
    ''').fetchall()
    
    # Get submissions by insurance type
    submissions_by_type = conn.execute('''
        SELECT insurance_type, COUNT(*) as count
        FROM form_submissions
        GROUP BY insurance_type
        ORDER BY count DESC
    ''').fetchall()
    
    # Get monthly submission trends
    monthly_trends = conn.execute('''
        SELECT strftime('%Y-%m', submission_date) as month, COUNT(*) as count
        FROM form_submissions
        WHERE submission_date >= date('now', '-12 months')
        GROUP BY strftime('%Y-%m', submission_date)
        ORDER BY month DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/dashboard.html',
                         total_submissions=total_submissions,
                         new_submissions=new_submissions,
                         total_blog_posts=total_blog_posts,
                         published_posts=published_posts,
                         recent_submissions=recent_submissions,
                         submissions_by_type=submissions_by_type,
                         monthly_trends=monthly_trends)

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
    conn = get_db_connection()
    query = 'SELECT * FROM form_submissions WHERE 1=1'
    params = []
    
    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)
    
    if insurance_type_filter:
        query += ' AND insurance_type = ?'
        params.append(insurance_type_filter)
    
    if date_from:
        query += ' AND date(submission_date) >= ?'
        params.append(date_from)
    
    if date_to:
        query += ' AND date(submission_date) <= ?'
        params.append(date_to)
    
    if search_query:
        query += ' AND (first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ?)'
        search_term = f'%{search_query}%'
        params.extend([search_term, search_term, search_term, search_term])
    
    # Get total count for pagination
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    total_count = conn.execute(count_query, params).fetchone()[0]
    
    # Get paginated results
    query += ' ORDER BY submission_date DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    submissions = conn.execute(query, params).fetchall()
    
    # Get filter options
    insurance_types = conn.execute('SELECT DISTINCT insurance_type FROM form_submissions').fetchall()
    conn.close()
    
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

@app.route('/admin/submissions/<int:submission_id>')
@admin_required
def admin_submission_detail(submission_id):
    """View submission detail"""
    conn = get_db_connection()
    submission = conn.execute('SELECT * FROM form_submissions WHERE id = ?', (submission_id,)).fetchone()
    conn.close()
    
    if not submission:
        flash('Submission not found', 'error')
        return redirect(url_for('admin_submissions'))
    
    return render_template('admin/submission_detail.html', submission=submission)

@app.route('/admin/submissions/<int:submission_id>/update', methods=['POST'])
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
        
        conn = get_db_connection()
        conn.execute('''
            UPDATE form_submissions
            SET status = ?, notes = ?, processed_by = ?, processed_date = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, notes, session['admin_username'], submission_id))
        
        conn.commit()
        conn.close()
        
        if request.is_json:
            return jsonify({"success": True, "message": "Submission updated successfully"})
        else:
            flash('Submission updated successfully', 'success')
            return redirect(url_for('admin_submission_detail', submission_id=submission_id))
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/admin/blog')
@admin_required
def admin_blog():
    """Manage blog posts"""
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    conn = get_db_connection()
    query = 'SELECT * FROM blog_posts WHERE 1=1'
    params = []
    
    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)
    
    if search_query:
        query += ' AND (title LIKE ? OR content LIKE ?)'
        search_term = f'%{search_query}%'
        params.extend([search_term, search_term])
    
    # Get total count
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    total_count = conn.execute(count_query, params).fetchone()[0]
    
    # Get paginated results
    query += ' ORDER BY created_date DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    posts = conn.execute(query, params).fetchall()
    
    conn.close()
    
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
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO blog_posts (title, slug, content, excerpt, status, featured_image, tags, meta_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, slug, content, excerpt, status, featured_image, tags, meta_description))
            
            conn.commit()
            flash('Blog post created successfully', 'success')
            return redirect(url_for('admin_blog'))
        except sqlite3.IntegrityError:
            flash('A blog post with this title already exists', 'error')
        finally:
            conn.close()
    
    return render_template('admin/blog_new.html')

@app.route('/admin/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_blog_edit(post_id):
    """Edit blog post"""
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM blog_posts WHERE id = ?', (post_id,)).fetchone()
    
    if not post:
        conn.close()
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
            conn.execute('''
                UPDATE blog_posts
                SET title = ?, slug = ?, content = ?, excerpt = ?, status = ?,
                    featured_image = ?, tags = ?, meta_description = ?, updated_date = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (title, slug, content, excerpt, status, featured_image, tags, meta_description, post_id))
            
            conn.commit()
            flash('Blog post updated successfully', 'success')
            return redirect(url_for('admin_blog'))
        except sqlite3.IntegrityError:
            flash('A blog post with this title already exists', 'error')
    
    conn.close()
    return render_template('admin/blog_edit.html', post=post)

@app.route('/admin/blog/<int:post_id>/status', methods=['POST'])
@admin_required
def admin_blog_status(post_id):
    """Update blog post status"""
    data = request.json
    new_status = data.get('status')
    
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM blog_posts WHERE id = ?', (post_id,)).fetchone()
    
    if post:
        # Update status
        update_query = 'UPDATE blog_posts SET status = ?, updated_date = CURRENT_TIMESTAMP'
        params = [new_status, post_id]
        
        # Set published date if status is published
        if new_status == 'published':
            update_query += ', published_date = CURRENT_TIMESTAMP'
        
        conn.execute(update_query, params)
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Status updated successfully"})
    else:
        conn.close()
        return jsonify({"success": False, "message": "Post not found"})

@app.route('/admin/blog/<int:post_id>/delete', methods=['POST'])
@admin_required
def admin_blog_delete(post_id):
    """Delete blog post"""
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM blog_posts WHERE id = ?', (post_id,)).fetchone()
    
    if post:
        conn.execute('DELETE FROM blog_posts WHERE id = ?', (post_id,))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Blog post deleted successfully'})
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'Blog post not found'}), 404

@app.route('/admin/export/submissions')
@admin_required
def admin_export_submissions():
    """Export submissions to CSV"""
    import csv
    from io import StringIO
    
    conn = get_db_connection()
    submissions = conn.execute('SELECT * FROM form_submissions ORDER BY submission_date DESC').fetchall()
    conn.close()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'First Name', 'Last Name', 'Phone', 'Email', 'Want To', 'Insurance Type',
                    'Submission Date', 'Status', 'Notes', 'Processed By', 'Processed Date'])
    
    # Write data
    for submission in submissions:
        writer.writerow([
            submission['id'], submission['first_name'], submission['last_name'],
            submission['phone'], submission['email'], submission['want_to'],
            submission['insurance_type'], submission['submission_date'], submission['status'],
            submission['notes'], submission['processed_by'], submission['processed_date']
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
    
    conn = get_db_connection()
    # Get top 5 admin sessions for audit log
    sessions = conn.execute('''
        SELECT * FROM admin_sessions
        ORDER BY login_time DESC
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    # Transform sessions to match template expectations
    logs = []
    for session in sessions:
        log_entry = {
            'id': session['id'],
            'action': 'LOGIN',
            'table_name': 'admin_sessions',
            'record_id': session['id'],
            'admin_user': session['admin_user'],
            'ip_address': session['ip_address'],
            'timestamp': session['login_time'],
            'old_values': None,
            'new_values': f"Session ID: {session['session_id']}, User Agent: {session['user_agent']}"
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
    
    conn = get_db_connection()
    # Export only top 5 sessions
    sessions = conn.execute('''
        SELECT * FROM admin_sessions
        ORDER BY login_time DESC
        LIMIT 5
    ''').fetchall()
    conn.close()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Admin User', 'Session ID', 'Login Time', 'Last Activity', 'IP Address', 'User Agent'])
    
    # Write data
    for session in sessions:
        writer.writerow([
            session['id'],
            session['admin_user'],
            session['session_id'],
            session['login_time'],
            session['last_activity'],
            session['ip_address'],
            session['user_agent']
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