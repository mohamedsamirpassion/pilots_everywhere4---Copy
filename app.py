from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_mail import Mail, Message
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DecimalField, DateTimeField, HiddenField, SelectMultipleField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import requests
import math
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
mail = Mail(app)

# Import models and forms
from models import db, User, PilotProfile, TruckingProfile, PilotLocation, Job, JobApplication, Trip, TripRating, SERVICE_TYPES, get_service_display_name, get_service_display_names
from forms import LoginForm, RegistrationForm, PilotProfileForm, TruckingProfileForm, LocationShareForm, JobPostForm, JobApplicationForm, TripRatingForm

# Initialize the database with the app
db.init_app(app)

# Make config available to templates
@app.context_processor
def inject_config():
    return dict(config=app.config)

# Utility functions
def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points in miles using Haversine formula with 20% buffer for oversize loads"""
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat/2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lng/2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    straight_line_distance = R * c
    
    # Add 20% buffer to account for oversize load routing restrictions
    # Oversize loads cannot take direct routes due to bridge heights, weight limits, etc.
    return straight_line_distance * 1.2

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Authentication Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)
        flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            user_type=form.user_type.data
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please complete your profile.', 'success')
        login_user(user)
        return redirect(url_for('profile'))
    
    return render_template('auth/register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Dashboard Routes

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'pilot':
        return redirect(url_for('pilot_dashboard'))
    elif current_user.user_type == 'trucking':
        return redirect(url_for('trucking_dashboard'))
    else:
        return redirect(url_for('profile'))

@app.route('/pilot/dashboard')
@login_required
def pilot_dashboard():
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    # Get pilot statistics
    pilot = current_user.pilot_profile
    active_applications = JobApplication.query.filter_by(pilot_id=pilot.id, status='pending').count()
    active_trips = Trip.query.filter_by(pilot_id=pilot.id, status='confirmed').count()
    completed_trips = Trip.query.filter_by(pilot_id=pilot.id, status='completed').count()
    
    # Get current location status
    current_location = PilotLocation.query.filter_by(pilot_id=pilot.id).filter(
        PilotLocation.expires_at > datetime.utcnow()
    ).first()
    
    return render_template('pilot/dashboard.html', 
                         pilot=pilot,
                         active_applications=active_applications,
                         active_trips=active_trips,
                         completed_trips=completed_trips,
                         current_location=current_location)

@app.route('/trucking/dashboard')
@login_required
def trucking_dashboard():
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    # Get trucking company statistics
    company = current_user.trucking_profile
    active_jobs = Job.query.filter_by(trucking_company_id=company.id, status='posted').count()
    active_trips = Trip.query.filter_by(trucking_company_id=company.id, status='confirmed').count()
    completed_trips = Trip.query.filter_by(trucking_company_id=company.id, status='completed').count()
    
    return render_template('trucking/dashboard.html',
                         company=company,
                         active_jobs=active_jobs,
                         active_trips=active_trips,
                         completed_trips=completed_trips)

# Profile Routes

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.user_type == 'pilot':
        if current_user.pilot_profile:
            form = PilotProfileForm(obj=current_user.pilot_profile)
        else:
            form = PilotProfileForm()
        
        if form.validate_on_submit():
            if current_user.pilot_profile:
                profile = current_user.pilot_profile
            else:
                profile = PilotProfile(user_id=current_user.id)
                db.session.add(profile)
            
            form.populate_obj(profile)
            profile.set_services_list(form.services.data)
            db.session.commit()
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('pilot_dashboard'))
        
        return render_template('pilot/profile.html', form=form)
    
    elif current_user.user_type == 'trucking':
        if current_user.trucking_profile:
            form = TruckingProfileForm(obj=current_user.trucking_profile)
        else:
            form = TruckingProfileForm()
        
        if form.validate_on_submit():
            if current_user.trucking_profile:
                profile = current_user.trucking_profile
            else:
                profile = TruckingProfile(user_id=current_user.id)
                db.session.add(profile)
            
            form.populate_obj(profile)
            db.session.commit()
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('trucking_dashboard'))
        
        return render_template('trucking/profile.html', form=form)

# Terms and Privacy Pages

@app.route('/terms')
def terms():
    return render_template('legal/terms.html')

@app.route('/privacy')
def privacy():
    return render_template('legal/privacy.html')

# Job Management Routes

@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    form = JobPostForm()
    if form.validate_on_submit():
        # Convert coordinates to float if provided, otherwise set to None
        pickup_lat = float(form.pickup_latitude.data) if form.pickup_latitude.data else None
        pickup_lng = float(form.pickup_longitude.data) if form.pickup_longitude.data else None
        delivery_lat = float(form.delivery_latitude.data) if form.delivery_latitude.data else None
        delivery_lng = float(form.delivery_longitude.data) if form.delivery_longitude.data else None
        
        # Calculate distance if coordinates are provided
        distance_miles = None
        if pickup_lat and pickup_lng and delivery_lat and delivery_lng:
            distance_miles = calculate_distance(pickup_lat, pickup_lng, delivery_lat, delivery_lng)
        
        job = Job(
            trucking_company_id=current_user.trucking_profile.id,
            pickup_address=form.pickup_address.data,
            pickup_latitude=pickup_lat,
            pickup_longitude=pickup_lng,
            delivery_address=form.delivery_address.data,
            delivery_latitude=delivery_lat,
            delivery_longitude=delivery_lng,
            pickup_datetime=form.pickup_datetime.data,
            distance_miles=distance_miles,
            rate_per_mile=form.rate_per_mile.data,
            rate_per_day=form.rate_per_day.data,
            overnight_rate=form.overnight_rate.data,
            nogo_rate=form.nogo_rate.data,
            description=form.description.data,
            status='posted'
        )
        job.set_services_required_list(form.services_required.data)
        
        db.session.add(job)
        db.session.commit()
        
        flash('Job posted successfully!', 'success')
        return redirect(url_for('manage_jobs'))
    
    return render_template('trucking/post_job.html', form=form)

@app.route('/manage-jobs')
@login_required
def manage_jobs():
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    company = current_user.trucking_profile
    # Eager load applications and pilot data to avoid N+1 queries
    jobs = Job.query.filter_by(trucking_company_id=company.id)\
        .options(db.joinedload(Job.applications).joinedload(JobApplication.pilot))\
        .order_by(Job.created_at.desc()).all()
    
    return render_template('trucking/manage_jobs.html', jobs=jobs)

@app.route('/trucking-trips')
@login_required
def trucking_trips():
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    company = current_user.trucking_profile
    trips = Trip.query.filter_by(trucking_company_id=company.id).order_by(Trip.created_at.desc()).all()
    
    return render_template('trucking/trips.html', trips=trips)

# Pilot Routes

@app.route('/pilot/jobs')
@login_required
def pilot_jobs():
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    pilot = current_user.pilot_profile
    applications = JobApplication.query.filter_by(pilot_id=pilot.id).order_by(JobApplication.applied_at.desc()).all()
    
    return render_template('pilot/jobs.html', applications=applications)

@app.route('/pilot/trips')
@login_required
def pilot_trips():
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    pilot = current_user.pilot_profile
    trips = Trip.query.filter_by(pilot_id=pilot.id).order_by(Trip.created_at.desc()).all()
    
    return render_template('pilot/trips.html', trips=trips)

@app.route('/trip/<int:trip_id>/confirm', methods=['POST'])
@login_required
def confirm_trip(trip_id):
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    trip = Trip.query.get_or_404(trip_id)
    pilot = current_user.pilot_profile
    
    # Check if pilot owns this trip
    if trip.pilot_id != pilot.id:
        flash('Access denied.', 'error')
        return redirect(url_for('pilot_trips'))
    
    # Only allow confirmation of confirmed trips
    if trip.status != 'confirmed':
        flash('Trip cannot be started.', 'error')
        return redirect(url_for('pilot_trips'))
    
    # Update trip status
    trip.status = 'in_progress'
    trip.started_at = datetime.utcnow()
    trip.pilot_confirmed = True
    
    # Now mark the job as assigned since pilot confirmed
    job = trip.job
    job.status = 'assigned'
    
    db.session.commit()
    flash('Trip started successfully! Safe travels.', 'success')
    return redirect(url_for('pilot_trips'))

@app.route('/trip/<int:trip_id>/complete', methods=['POST'])
@login_required
def complete_trip(trip_id):
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    trip = Trip.query.get_or_404(trip_id)
    pilot = current_user.pilot_profile
    
    # Check if pilot owns this trip
    if trip.pilot_id != pilot.id:
        flash('Access denied.', 'error')
        return redirect(url_for('pilot_trips'))
    
    # Only allow completion of in-progress trips
    if trip.status != 'in_progress':
        flash('Trip cannot be completed.', 'error')
        return redirect(url_for('pilot_trips'))
    
    # Update trip status
    trip.status = 'completed'
    trip.completed_at = datetime.utcnow()
    
    db.session.commit()
    flash('Trip completed successfully! Thank you for your service.', 'success')
    return redirect(url_for('pilot_trips'))

@app.route('/trip/<int:trip_id>/rate-company', methods=['GET', 'POST'])
@login_required
def rate_company(trip_id):
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    trip = Trip.query.get_or_404(trip_id)
    pilot = current_user.pilot_profile
    
    # Check if pilot owns this trip
    if trip.pilot_id != pilot.id:
        flash('Access denied.', 'error')
        return redirect(url_for('pilot_trips'))
    
    # Only allow rating of completed trips
    if trip.status != 'completed':
        flash('Trip must be completed before rating.', 'error')
        return redirect(url_for('pilot_trips'))
    
    # Check if already rated
    existing_rating = TripRating.query.filter_by(
        trip_id=trip_id, 
        rated_by='pilot'
    ).first()
    
    if existing_rating:
        flash('You have already rated this company.', 'info')
        return redirect(url_for('pilot_trips'))
    
    from forms import TripRatingForm
    form = TripRatingForm()
    
    if form.validate_on_submit():
        # Create new rating
        rating = TripRating(
            trip_id=trip.id,
            pilot_id=pilot.id,
            trucking_company_id=trip.trucking_company_id,
            company_rating=form.rating.data,
            company_review=form.review.data,
            rated_by='pilot'
        )
        
        db.session.add(rating)
        
        # Update company's overall rating
        company = trip.trucking_company
        all_ratings = TripRating.query.filter_by(
            trucking_company_id=company.id
        ).filter(TripRating.company_rating.isnot(None)).all()
        
        if all_ratings:
            total_ratings = sum(r.company_rating for r in all_ratings)
            company.rating = round(total_ratings / len(all_ratings), 1)
            company.rating_count = len(all_ratings)
        
        db.session.commit()
        flash('Thank you for your rating!', 'success')
        return redirect(url_for('pilot_trips'))
    
    return render_template('pilot/rate_company.html', form=form, trip=trip)

@app.route('/trip/<int:trip_id>/rate-pilot', methods=['GET', 'POST'])
@login_required
def rate_pilot(trip_id):
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    trip = Trip.query.get_or_404(trip_id)
    company = current_user.trucking_profile
    
    # Check if company owns this trip
    if trip.trucking_company_id != company.id:
        flash('Access denied.', 'error')
        return redirect(url_for('trucking_trips'))
    
    # Only allow rating of completed trips
    if trip.status != 'completed':
        flash('Trip must be completed before rating.', 'error')
        return redirect(url_for('trucking_trips'))
    
    # Check if already rated
    existing_rating = TripRating.query.filter_by(
        trip_id=trip_id, 
        rated_by='trucking'
    ).first()
    
    if existing_rating:
        flash('You have already rated this pilot.', 'info')
        return redirect(url_for('trucking_trips'))
    
    from forms import TripRatingForm
    form = TripRatingForm()
    
    if form.validate_on_submit():
        # Create new rating
        rating = TripRating(
            trip_id=trip.id,
            pilot_id=trip.pilot_id,
            trucking_company_id=company.id,
            pilot_rating=form.rating.data,
            pilot_review=form.review.data,
            rated_by='trucking'
        )
        
        db.session.add(rating)
        
        # Update pilot's overall rating
        pilot = trip.pilot
        all_ratings = TripRating.query.filter_by(
            pilot_id=pilot.id
        ).filter(TripRating.pilot_rating.isnot(None)).all()
        
        if all_ratings:
            total_ratings = sum(r.pilot_rating for r in all_ratings)
            pilot.rating = round(total_ratings / len(all_ratings), 1)
            pilot.rating_count = len(all_ratings)
        
        db.session.commit()
        flash('Thank you for your rating!', 'success')
        return redirect(url_for('trucking_trips'))
    
    return render_template('trucking/rate_pilot.html', form=form, trip=trip)

@app.route('/pilot/share-location', methods=['GET', 'POST'])
@login_required
def pilot_share_location():
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    form = LocationShareForm()
    pilot = current_user.pilot_profile
    
    # Get current location if exists
    current_location = PilotLocation.query.filter_by(pilot_id=pilot.id).filter(
        PilotLocation.expires_at > datetime.utcnow()
    ).first()
    
    if form.validate_on_submit():
        # Validate that latitude and longitude are provided
        if not form.latitude.data or not form.longitude.data:
            flash('Please select a location on the map or use GPS to set your coordinates.', 'error')
            return render_template('pilot/share_location.html', form=form, current_location=current_location)
        
        try:
            # Convert coordinates to float
            latitude = float(form.latitude.data)
            longitude = float(form.longitude.data)
        except (ValueError, TypeError):
            flash('Invalid coordinates provided. Please select a valid location.', 'error')
            return render_template('pilot/share_location.html', form=form, current_location=current_location)
        
        # Remove existing location
        if current_location:
            db.session.delete(current_location)
        
        # Create new location
        location = PilotLocation(
            pilot_id=pilot.id,
            latitude=latitude,
            longitude=longitude,
            address=form.address.data,
            coverage_radius=form.coverage_radius.data,
            expires_at=datetime.utcnow() + timedelta(hours=48)
        )
        location.set_services_available_list(form.services_available.data)
        
        db.session.add(location)
        db.session.commit()
        
        flash('Location shared successfully! It will be visible to trucking companies for 48 hours.', 'success')
        return redirect(url_for('pilot_dashboard'))
    
    # Pre-populate form with current location if exists
    if current_location:
        form.latitude.data = current_location.latitude
        form.longitude.data = current_location.longitude
        form.address.data = current_location.address
        form.coverage_radius.data = current_location.coverage_radius
        form.services_available.data = current_location.get_services_available_list()
    
    return render_template('pilot/share_location.html', form=form, current_location=current_location)

@app.route('/pilot/stop-sharing-location')
@login_required
def pilot_stop_sharing_location():
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    pilot = current_user.pilot_profile
    
    # Find and delete current location
    current_location = PilotLocation.query.filter_by(pilot_id=pilot.id).filter(
        PilotLocation.expires_at > datetime.utcnow()
    ).first()
    
    if current_location:
        db.session.delete(current_location)
        db.session.commit()
        flash('Location sharing stopped successfully. You are no longer visible to trucking companies.', 'success')
    else:
        flash('No active location sharing found.', 'info')
    
    return redirect(url_for('pilot_dashboard'))

@app.route('/pilot/quick-share-location', methods=['POST'])
@login_required
def pilot_quick_share_location():
    if current_user.user_type != 'pilot':
        return jsonify({'error': 'Access denied'}), 403
    
    if not current_user.pilot_profile:
        return jsonify({'error': 'Please complete your profile first'}), 400
    
    pilot = current_user.pilot_profile
    
    # Get location data from request
    data = request.get_json()
    if not data or 'latitude' not in data or 'longitude' not in data:
        return jsonify({'error': 'Location data required'}), 400
    
    try:
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid location coordinates'}), 400
    
    # Validate coordinates
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return jsonify({'error': 'Invalid location coordinates'}), 400
    
    # Get pilot's services from their profile
    if not pilot.services:
        return jsonify({'error': 'No services configured in your profile. Please update your profile first.'}), 400
    
    # Remove any existing location
    existing_location = PilotLocation.query.filter_by(pilot_id=pilot.id).filter(
        PilotLocation.expires_at > datetime.utcnow()
    ).first()
    
    if existing_location:
        db.session.delete(existing_location)
    
    # Create new location with pilot's profile services
    new_location = PilotLocation(
        pilot_id=pilot.id,
        latitude=latitude,
        longitude=longitude,
        address=data.get('address', ''),
        services_available=pilot.services,  # Use services from pilot's profile
        coverage_radius=300,  # Default 300 miles
        expires_at=datetime.utcnow() + timedelta(hours=48)
    )
    
    db.session.add(new_location)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Location shared successfully! You are now visible to trucking companies for 48 hours.',
        'services': new_location.get_services_available_display(),
        'expires_at': new_location.expires_at.isoformat()
    })

@app.route('/job/<int:job_id>')
def job_details(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Check if user has access to view this job
    if current_user.is_authenticated:
        user_type = current_user.user_type
        
        # If trucking company, check if they own this job
        if user_type == 'trucking' and current_user.trucking_profile:
            is_owner = (job.trucking_company_id == current_user.trucking_profile.id)
        else:
            is_owner = False
            
        # Get applications if user is trucking company and owns the job
        applications = []
        if is_owner:
            applications = JobApplication.query.filter_by(job_id=job_id).order_by(JobApplication.applied_at.desc()).all()
            # Sort by distance (closest first), then by application time
            # Applications without location go to the end
            applications.sort(key=lambda app: (
                app.get_pilot_distance_to_pickup() is None,  # None values go to end
                app.get_pilot_distance_to_pickup() or float('inf')  # Sort by distance
            ))
    else:
        user_type = None
        is_owner = False
        applications = []
    
    return render_template('job_details.html', job=job, user_type=user_type, is_owner=is_owner, applications=applications)

@app.route('/job/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    job = Job.query.get_or_404(job_id)
    company = current_user.trucking_profile
    
    # Check if user owns this job
    if job.trucking_company_id != company.id:
        flash('Access denied.', 'error')
        return redirect(url_for('manage_jobs'))
    
    # Don't allow editing if job has applications or is not posted
    if job.status != 'posted':
        flash('Cannot edit job that is not in posted status.', 'error')
        return redirect(url_for('job_details', job_id=job_id))
    
    applications_count = JobApplication.query.filter_by(job_id=job_id).count()
    if applications_count > 0:
        flash('Cannot edit job that already has applications.', 'warning')
        return redirect(url_for('job_details', job_id=job_id))
    
    form = JobPostForm(obj=job)
    if form.validate_on_submit():
        form.populate_obj(job)
        job.set_services_required_list(form.services_required.data)
        job.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Job updated successfully!', 'success')
        return redirect(url_for('job_details', job_id=job_id))
    
    # Pre-populate form with existing data
    if job.services_required:
        form.services_required.data = json.loads(job.services_required)
    
    return render_template('trucking/edit_job.html', form=form, job=job)

@app.route('/job/<int:job_id>/applications')
@login_required
def job_applications(job_id):
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    job = Job.query.get_or_404(job_id)
    company = current_user.trucking_profile
    
    # Check if user owns this job
    if job.trucking_company_id != company.id:
        flash('Access denied.', 'error')
        return redirect(url_for('manage_jobs'))
    
    applications = JobApplication.query.filter_by(job_id=job_id).order_by(JobApplication.applied_at.desc()).all()
    
    return render_template('trucking/job_applications.html', job=job, applications=applications)

@app.route('/application/<int:application_id>/respond', methods=['POST'])
@login_required
def respond_to_application(application_id):
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    application = JobApplication.query.get_or_404(application_id)
    job = application.job
    company = current_user.trucking_profile
    
    # Check if user owns this job
    if job.trucking_company_id != company.id:
        flash('Access denied.', 'error')
        return redirect(url_for('manage_jobs'))
    
    action = request.form.get('action')
    if action not in ['approve', 'reject']:
        flash('Invalid action.', 'error')
        return redirect(url_for('job_details', job_id=job.id))
    
    if action == 'approve':
        # Check if job is still available
        if job.status != 'posted':
            flash('This job is no longer available.', 'error')
            return redirect(url_for('job_details', job_id=job.id))
        
        # Approve this application
        application.status = 'approved'
        application.responded_at = datetime.utcnow()
        
        # Create trip
        trip = Trip(
            job_id=job.id,
            pilot_id=application.pilot_id,
            trucking_company_id=company.id,
            status='confirmed',
            agreed_rate_per_mile=application.proposed_rate_per_mile or job.rate_per_mile,
            agreed_rate_per_day=application.proposed_rate_per_day or job.rate_per_day,
            agreed_overnight_rate=application.proposed_overnight_rate or job.overnight_rate,
            agreed_nogo_rate=application.proposed_nogo_rate or job.nogo_rate,
            allow_rate_mixing=job.allow_rate_mixing
        )
        db.session.add(trip)
        
        # Don't update job status yet - wait for pilot confirmation
        # job.status = 'assigned'  # Removed - job stays 'posted' until pilot confirms
        
        # Reject all other applications for this job
        other_applications = JobApplication.query.filter(
            JobApplication.job_id == job.id,
            JobApplication.id != application_id,
            JobApplication.status == 'pending'
        ).all()
        
        for other_app in other_applications:
            other_app.status = 'rejected'
            other_app.responded_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Application approved! Trip created with {application.pilot.contact_name}.', 'success')
    
    elif action == 'reject':
        application.status = 'rejected'
        application.responded_at = datetime.utcnow()
        db.session.commit()
        flash('Application rejected.', 'info')
    
    return redirect(url_for('job_details', job_id=job.id))

@app.route('/job/<int:job_id>/cancel', methods=['POST'])
@login_required
def cancel_job(job_id):
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    job = Job.query.get_or_404(job_id)
    company = current_user.trucking_profile
    
    # Check if user owns this job
    if job.trucking_company_id != company.id:
        flash('Access denied.', 'error')
        return redirect(url_for('manage_jobs'))
    
    # Only allow cancellation of posted jobs
    if job.status != 'posted':
        flash('Cannot cancel job that is not in posted status.', 'error')
        return redirect(url_for('job_details', job_id=job_id))
    
    # Update job status
    job.status = 'cancelled'
    job.updated_at = datetime.utcnow()
    
    # Reject all pending applications
    applications = JobApplication.query.filter_by(job_id=job_id, status='pending').all()
    for application in applications:
        application.status = 'rejected'
        application.responded_at = datetime.utcnow()
    
    db.session.commit()
    flash('Job cancelled successfully.', 'success')
    return redirect(url_for('manage_jobs'))

@app.route('/job/<int:job_id>/mark-covered', methods=['POST'])
@login_required
def mark_job_covered(job_id):
    if current_user.user_type != 'trucking':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.trucking_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    job = Job.query.get_or_404(job_id)
    company = current_user.trucking_profile
    
    # Check if user owns this job
    if job.trucking_company_id != company.id:
        flash('Access denied.', 'error')
        return redirect(url_for('manage_jobs'))
    
    # Only allow marking as covered for posted jobs
    if job.status != 'posted':
        flash('Cannot mark job as covered that is not in posted status.', 'error')
        return redirect(url_for('job_details', job_id=job_id))
    
    # Update job status
    job.status = 'covered'
    job.updated_at = datetime.utcnow()
    
    # Reject all pending applications
    applications = JobApplication.query.filter_by(job_id=job_id, status='pending').all()
    for application in applications:
        application.status = 'rejected'
        application.responded_at = datetime.utcnow()
    
    db.session.commit()
    flash('Job marked as covered successfully.', 'success')
    return redirect(url_for('manage_jobs'))

@app.route('/pilot/apply/<int:job_id>', methods=['GET', 'POST'])
@login_required
def pilot_apply_job(job_id):
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    job = Job.query.get_or_404(job_id)
    pilot = current_user.pilot_profile
    
    # Check if job is still available
    if job.status != 'posted':
        flash('This job is no longer available.', 'error')
        return redirect(url_for('pilot_jobs'))
    
    # Check if pilot has already applied
    existing_application = JobApplication.query.filter_by(job_id=job_id, pilot_id=pilot.id).first()
    if existing_application:
        flash('You have already applied to this job.', 'warning')
        return redirect(url_for('pilot_jobs'))
    
    form = JobApplicationForm()
    if form.validate_on_submit():
        application = JobApplication(
            job_id=job_id,
            pilot_id=pilot.id,
            proposed_rate_per_mile=form.proposed_rate_per_mile.data,
            proposed_rate_per_day=form.proposed_rate_per_day.data,
            proposed_overnight_rate=form.proposed_overnight_rate.data,
            proposed_nogo_rate=form.proposed_nogo_rate.data,
            message=form.message.data,
            status='pending'
        )
        
        db.session.add(application)
        db.session.commit()
        
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('pilot_jobs'))
    
    return render_template('pilot/apply_job.html', job=job, form=form)

@app.route('/pilot/application/<int:application_id>/withdraw', methods=['POST'])
@login_required
def pilot_withdraw_application(application_id):
    if current_user.user_type != 'pilot':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.pilot_profile:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('profile'))
    
    application = JobApplication.query.get_or_404(application_id)
    pilot = current_user.pilot_profile
    
    # Check if pilot owns this application
    if application.pilot_id != pilot.id:
        flash('Access denied.', 'error')
        return redirect(url_for('pilot_jobs'))
    
    # Only allow withdrawal of pending applications
    if application.status != 'pending':
        flash('Cannot withdraw application that is not pending.', 'error')
        return redirect(url_for('pilot_jobs'))
    
    # Update application status
    application.status = 'withdrawn'
    application.responded_at = datetime.utcnow()
    
    db.session.commit()
    flash('Application withdrawn successfully.', 'success')
    return redirect(url_for('pilot_jobs'))

# API Routes for Map Data

@app.route('/api/pilots/locations')
@login_required
def api_pilots_locations():
    if current_user.user_type != 'trucking':
        return jsonify({'error': 'Access denied'}), 403
    
    # Get all active pilot locations
    locations = db.session.query(PilotLocation).join(PilotProfile).filter(
        PilotLocation.expires_at > datetime.utcnow()
    ).all()
    
    pilots_data = []
    for location in locations:
        pilot = location.pilot
        pilots_data.append({
            'id': pilot.id,
            'latitude': location.latitude,
            'longitude': location.longitude,
            'company_name': pilot.company_name,
            # Contact info hidden until job agreement
            'services': location.get_services_available_display(),
            'coverage_radius': location.coverage_radius,
            'rating': pilot.dynamic_rating,
            'rating_count': pilot.dynamic_rating_count,
            'expires_at': location.expires_at.isoformat()
        })
    
    return jsonify(pilots_data)

@app.route('/api/jobs/active')
@login_required
def api_jobs_active():
    if current_user.user_type != 'pilot':
        return jsonify({'error': 'Access denied'}), 403
    
    # Get all active jobs
    jobs = Job.query.filter_by(status='posted').all()
    
    jobs_data = []
    for job in jobs:
        jobs_data.append({
            'id': job.id,
            'pickup_address': job.pickup_address,
            'pickup_latitude': job.pickup_latitude,
            'pickup_longitude': job.pickup_longitude,
            'delivery_address': job.delivery_address,
            'pickup_datetime': job.pickup_datetime.isoformat(),
            'services_required': job.get_services_required_display(),
            'rate_per_mile': float(job.rate_per_mile) if job.rate_per_mile else None,
            'rate_per_day': float(job.rate_per_day) if job.rate_per_day else None,
            'overnight_rate': float(job.overnight_rate) if job.overnight_rate else None,
            'distance_miles': job.distance_miles,
            # Company name hidden until job confirmation for privacy
        })
    
    return jsonify(jobs_data)

@app.route('/api/trips')
@login_required 
def api_trips():
    """API endpoint for getting trips data"""
    if current_user.user_type == 'pilot':
        trips = Trip.query.filter_by(pilot_id=current_user.pilot_profile.id).all()
    elif current_user.user_type == 'trucking':
        trips = Trip.query.filter_by(trucking_company_id=current_user.trucking_profile.id).all()
    else:
        return jsonify({'error': 'Access denied'}), 403
    
    trips_data = []
    for trip in trips:
        trips_data.append({
            'id': trip.id,
            'status': trip.status,
            'pickup_address': trip.job.pickup_address,
            'delivery_address': trip.job.delivery_address,
            'pickup_datetime': trip.job.pickup_datetime.isoformat(),
            'distance_miles': trip.distance_miles,
            'agreed_rate_per_mile': float(trip.agreed_rate_per_mile) if trip.agreed_rate_per_mile else None,
            'agreed_rate_per_day': float(trip.agreed_rate_per_day) if trip.agreed_rate_per_day else None
        })
    
    return jsonify(trips_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 