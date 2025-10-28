from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, logout_user, LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

import os

# ----------------- Flask App Setup -----------------
app = Flask(__name__)
app.secret_key = 'hmsprojects'

login_manager = LoginManager(app) # handling user authentication
# Set the default view to redirect to when login is required
login_manager.login_view = 'login'

# ----------------- Database Setup -----------------
# Configure database connection URI for MySQL
# Format: mysql://username:password@host/database_names
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/hms23bce2304'
db = SQLAlchemy(app)

# ----------------- Models -----------------
# Test model - likely for testing database connection
class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))


# User model for authentication - inherits from UserMixin (provides default implementations for Flask-Login)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    usertype = db.Column(db.String(50)) # Type of user (Doctor/Patient)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(1000))

class Patients(db.Model):
    pid = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50))
    name = db.Column(db.String(50))
    gender = db.Column(db.String(50))
    slot = db.Column(db.String(50))
    disease = db.Column(db.String(50))
    time = db.Column(db.String(50), nullable=False) # Appointment time (required)
    date = db.Column(db.String(50), nullable=False) # Appointment date (required)
    dept = db.Column(db.String(50))
    number = db.Column(db.String(50))

class Doctors(db.Model):
    did = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50))
    doctorname = db.Column(db.String(50))
    dept = db.Column(db.String(50))


# Trigr model for audit logging (tracks changes to appointments)
class Trigr(db.Model):
    tid = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.Integer)
    email = db.Column(db.String(50))
    name = db.Column(db.String(50))
    action = db.Column(db.String(50))
    timestamp = db.Column(db.String(50))

# ----------------- Login Manager -----------------
# This function is required by Flask-Login to load a user from the database
@login_manager.user_loader
def load_user(user_id):
    # Query and return user by ID, Flask-Login uses this to manage sessions
    return User.query.get(int(user_id))

# ----------------- Routes -----------------
@app.route('/')
def index():
    return render_template('index.html')


# Doctors registration route - accepts both POST and GET methods
@app.route('/doctors', methods=['POST','GET'])
def doctors():
    # Check if form was submitted via POST method
    if request.method == "POST":
        # Get form data from request
        email = request.form.get('email')
        doctorname = request.form.get('doctorname')
        dept = request.form.get('dept')

        # Create new doctor object with form data
        new_doctor = Doctors(email=email, doctorname=doctorname, dept=dept)
        db.session.add(new_doctor)  # Add new doctor to database session
        db.session.commit() # Commit changes to database
        flash("Information is Stored", "primary") # Flash success message to user

    # Render doctor registration template (for both GET and POST)
    return render_template('doctor.html')


# Patient appointment booking route - requires user to be logged in
@app.route('/patients', methods=['POST','GET'])
@login_required # Decorator ensures user must be logged in to access this route
def patient():
    # Query all doctors to display in the form
    doct = Doctors.query.all()

    if request.method == "POST":
        email = request.form.get('email')
        name = request.form.get('name')
        gender = request.form.get('gender')
        slot = request.form.get('slot')
        disease = request.form.get('disease')
        time = request.form.get('time')
        date = request.form.get('date')
        dept = request.form.get('dept')
        number = request.form.get('number')

        # Validate phone number length
        if len(number) != 10:
            flash("Please provide a 10-digit number", "warning")
            return render_template('patient.html', doct=doct)

        # Create new patient appointment object
        new_patient = Patients(email=email, name=name, gender=gender, slot=slot,
        disease=disease, time=time, date=date, dept=dept, number=number)
        db.session.add(new_patient) # Add to database session
        db.session.commit()

        flash("Booking Confirmed", "info") # Flash confirmation message, info-blue colour

    # Render patient booking template with list of doctors
    return render_template('patient.html', doct=doct)

# Appointments viewing route - requires login
@app.route('/bookings')
@login_required
def bookings():
    em = current_user.email # Get current user's email
    if current_user.usertype == "Doctor":
        # Doctors can see all appointments
        query = Patients.query.all()  # All patients for doctors
    else:
        # Patients can only see their own appointments
        query = Patients.query.filter_by(email=em).all()  # Only current user's bookings
    # Render bookings template with the appropriate query results    
    return render_template('booking.html', query=query)
    

@app.route("/edit/<int:pid>", methods=['POST','GET'])
@login_required
def edit(pid):
    # Find the patient appointment by ID
    post = Patients.query.filter_by(pid=pid).first()
    if request.method == "POST":
        post.email = request.form.get('email')
        post.name = request.form.get('name')
        post.gender = request.form.get('gender')
        post.slot = request.form.get('slot')
        post.disease = request.form.get('disease')
        post.time = request.form.get('time')
        post.date = request.form.get('date')
        post.dept = request.form.get('dept')
        post.number = request.form.get('number')
        db.session.commit()
        flash("Slot Updated", "success")
        return redirect('/bookings')   # Redirect to bookings page
    
    # For GET request, render edit form with current data
    return render_template('edit.html', posts=post)


# Find the patient appointment by ID
@app.route("/delete/<int:pid>", methods=['POST','GET'])
@login_required
def delete(pid):
    patient = Patients.query.filter_by(pid=pid).first()
    # Check if patient exists
    if patient:
        db.session.delete(patient)  # Delete from database session
        db.session.commit()
        flash("Slot Deleted Successfully", "danger")
    return redirect('/bookings') # Redirect back to bookings page

# User registration/signup route
@app.route('/signup', methods=['POST','GET'])
def signup():
    # Check if form was submitted
    if request.method == "POST":
        # Get form data
        username = request.form.get('username')
        usertype = request.form.get('usertype')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if email already exists in database
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email Already Exists", "warning")
            # Re-render signup form with error
            return render_template('signup.html')
        # Create new user with plain text password
        new_user = User(username=username, usertype=usertype, email=email, password=password)
        db.session.add(new_user) # Add to database
        db.session.commit()
        flash("Signup Successful, Please Login", "success")
        return render_template('login.html')
    
    # For GET request, render signup form
    return render_template('signup.html')

@app.route('/login', methods=['POST','GET'])
def login():
    # Check if form was submitted
    if request.method == "POST":
        # Get login credentials
        email = request.form.get('email')
        password = request.form.get('password')
        # Find user by email
        user = User.query.filter_by(email=email).first()

        # Check if user exists and password matches
        if user and user.password == password:
            # Log the user in (creates session)
            login_user(user)
            flash("Login Success", "primary")
            return redirect(url_for('index'))# Redirect to home page
        else:
            flash("Invalid credentials", "danger")
            return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
@login_required # User must be logged in to logout
def logout():
    # Log the user out (clears session)
    logout_user()
    flash("Logout Successful", "warning")
    return redirect(url_for('login'))

# Database connection test route
@app.route('/test')
def test():
    try:
        # Try to query Test table to check database connection
        Test.query.all()
        return 'Database Connected'
    except:
        return 'Database Not Connected'

# Audit logs viewing route
@app.route('/details')
@login_required
def details():
    # Get all audit log entries
    posts = Trigr.query.all()
    # Render audit logs template
    return render_template('trigers.html', posts=posts)

# Doctor search route
@app.route('/search', methods=['POST','GET'])
@login_required
def search():
    # Check if search form was submitted
    if request.method == "POST":
        query = request.form.get('search')
        # Search by department
        dept = Doctors.query.filter_by(dept=query).first()
        # Search by doctor name
        name = Doctors.query.filter_by(doctorname=query).first()
        if name:
            flash("Doctor is Available", "info")
        else:
            flash("Doctor is Not Available", "danger")
    return render_template('index.html')

# ----------------- Run App -----------------
# This ensures the app only runs when executed directly, not when imported
if __name__ == '__main__':
    # Run the Flask application with debug mode enabled
    # Debug mode provides detailed error pages and auto-reloads on code changes
    app.run(debug=True)
