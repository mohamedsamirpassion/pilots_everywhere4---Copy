from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'pilot' or 'trucking'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    pilot_profile = db.relationship('PilotProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    trucking_profile = db.relationship('TruckingProfile', backref='user', uselist=False, cascade='all, delete-orphan')

class PilotProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    services = db.Column(db.Text)  # JSON string of service types
    equipment_details = db.Column(db.Text)
    certifications = db.Column(db.Text)
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    subscription_active = db.Column(db.Boolean, default=True)
    subscription_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    locations = db.relationship('PilotLocation', backref='pilot', cascade='all, delete-orphan')
    applications = db.relationship('JobApplication', backref='pilot', cascade='all, delete-orphan')
    trips_as_pilot = db.relationship('Trip', backref='pilot', cascade='all, delete-orphan')
    
    def get_services_list(self):
        if self.services:
            return json.loads(self.services)
        return []
    
    def set_services_list(self, services_list):
        self.services = json.dumps(services_list)
    
    @property
    def dynamic_rating(self):
        """Calculate current rating from all ratings"""
        pilot_ratings = [r.pilot_rating for r in self.ratings if r.pilot_rating is not None]
        if pilot_ratings:
            return round(sum(pilot_ratings) / len(pilot_ratings), 1)
        return 0.0
    
    @property
    def dynamic_rating_count(self):
        """Count of all ratings received"""
        return len([r for r in self.ratings if r.pilot_rating is not None])

class TruckingProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    dot_number = db.Column(db.String(20))
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    jobs = db.relationship('Job', backref='trucking_company', cascade='all, delete-orphan')
    trips_as_company = db.relationship('Trip', backref='trucking_company', cascade='all, delete-orphan')
    
    @property
    def dynamic_rating(self):
        """Calculate current rating from all ratings"""
        company_ratings = [r.company_rating for r in self.ratings if r.company_rating is not None]
        if company_ratings:
            return round(sum(company_ratings) / len(company_ratings), 1)
        return 0.0
    
    @property
    def dynamic_rating_count(self):
        """Count of all ratings received"""
        return len([r for r in self.ratings if r.company_rating is not None])

class PilotLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot_profile.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(500))
    services_available = db.Column(db.Text)  # JSON string of available service types at this location
    coverage_radius = db.Column(db.Integer, default=300)  # Coverage radius in miles (100-700)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_services_available_list(self):
        if self.services_available:
            return json.loads(self.services_available)
        return []
    
    def get_services_available_display(self):
        """Get services with proper display names"""
        service_keys = self.get_services_available_list()
        return get_service_display_names(service_keys)
    
    def set_services_available_list(self, services_list):
        self.services_available = json.dumps(services_list)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trucking_company_id = db.Column(db.Integer, db.ForeignKey('trucking_profile.id'), nullable=False)
    pickup_address = db.Column(db.String(500), nullable=False)
    pickup_latitude = db.Column(db.Float, nullable=False)
    pickup_longitude = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.String(500), nullable=False)
    delivery_latitude = db.Column(db.Float, nullable=False)
    delivery_longitude = db.Column(db.Float, nullable=False)
    pickup_datetime = db.Column(db.DateTime, nullable=False)
    distance_miles = db.Column(db.Float)
    services_required = db.Column(db.Text, nullable=False)  # JSON string of required service types
    rate_per_mile = db.Column(db.Float)
    rate_per_day = db.Column(db.Float)
    overnight_rate = db.Column(db.Float)
    nogo_rate = db.Column(db.Float)
    allow_rate_mixing = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='posted')  # 'posted', 'covered', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('JobApplication', backref='job', cascade='all, delete-orphan')
    trip = db.relationship('Trip', backref='job', uselist=False, cascade='all, delete-orphan')
    
    def get_services_required_list(self):
        if self.services_required:
            return json.loads(self.services_required)
        return []
    
    def get_services_required_display(self):
        """Get services with proper display names"""
        service_keys = self.get_services_required_list()
        return get_service_display_names(service_keys)
    
    def set_services_required_list(self, services_list):
        self.services_required = json.dumps(services_list)

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot_profile.id'), nullable=False)
    proposed_rate_per_mile = db.Column(db.Float)
    proposed_rate_per_day = db.Column(db.Float)
    proposed_overnight_rate = db.Column(db.Float)
    proposed_nogo_rate = db.Column(db.Float)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected'
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    
    def get_pilot_distance_to_pickup(self):
        """Calculate distance from pilot's current location to job pickup"""
        import math
        
        # Get pilot's current active location
        current_location = PilotLocation.query.filter_by(pilot_id=self.pilot_id).filter(
            PilotLocation.expires_at > datetime.utcnow()
        ).first()
        
        if not current_location or not self.job.pickup_latitude or not self.job.pickup_longitude:
            return None
            
        # Calculate distance using Haversine formula
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(current_location.latitude)
        lat2_rad = math.radians(self.job.pickup_latitude)
        delta_lat = math.radians(self.job.pickup_latitude - current_location.latitude)
        delta_lng = math.radians(self.job.pickup_longitude - current_location.longitude)
        
        a = (math.sin(delta_lat/2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lng/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = R * c
        return round(distance, 1)  # Round to 1 decimal place

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot_profile.id'), nullable=False)
    trucking_company_id = db.Column(db.Integer, db.ForeignKey('trucking_profile.id'), nullable=False)
    agreed_rate_per_mile = db.Column(db.Float)
    agreed_rate_per_day = db.Column(db.Float)
    agreed_overnight_rate = db.Column(db.Float)
    agreed_nogo_rate = db.Column(db.Float)
    allow_rate_mixing = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='confirmed')  # 'confirmed', 'in_progress', 'completed', 'cancelled'
    pilot_confirmed = db.Column(db.Boolean, default=False)
    company_confirmed = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ratings = db.relationship('TripRating', backref='trip', cascade='all, delete-orphan')

class TripRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot_profile.id'), nullable=False)
    trucking_company_id = db.Column(db.Integer, db.ForeignKey('trucking_profile.id'), nullable=False)
    pilot_rating = db.Column(db.Float)  # Rating given to pilot (1-5)
    company_rating = db.Column(db.Float)  # Rating given to trucking company (1-5)
    pilot_review = db.Column(db.Text)  # Review of pilot
    company_review = db.Column(db.Text)  # Review of trucking company
    rated_by = db.Column(db.String(20), nullable=False)  # 'pilot' or 'trucking'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    pilot = db.relationship('PilotProfile', backref='ratings')
    trucking_company = db.relationship('TruckingProfile', backref='ratings')

# Service types constants
SERVICE_TYPES = [
    ('chase_car', 'Chase Car'),
    ('lead_car', 'Lead Car'),
    ('height_pole', 'Height Pole'),
    ('steer_car', 'Steer Car'),
    ('route_survey', 'Route Survey'),
    ('cevo', 'CEVO (PA Certified)')
]

# Helper function to get service display name
def get_service_display_name(service_key):
    """Convert service key to display name"""
    service_dict = dict(SERVICE_TYPES)
    return service_dict.get(service_key, service_key.replace('_', ' ').title())

# Helper function to get service display names from list
def get_service_display_names(service_keys):
    """Convert list of service keys to display names"""
    return [get_service_display_name(key) for key in service_keys] 