[![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/mohamedsamirpassion/pilots_everywhere4---Copy?utm_source=oss&utm_medium=github&utm_campaign=mohamedsamirpassion%2Fpilots_everywhere4---Copy&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)](https://coderabbit.ai)

# Pilots Everywhere

A comprehensive web application that connects trucking companies with certified pilot car escorts for oversize load transportation across North America.

## Features

### For Pilot Car Operators
- **Location Sharing**: Share your GPS location or select on map with 48-hour expiry
- **Coverage Radius**: Set coverage area from 100-700 miles for job notifications
- **Job Discovery**: Browse available jobs on interactive map and job lists
- **Service Management**: Offer multiple services (Chase Car, Lead Car, Height Pole, etc.)
- **Rate Negotiation**: Flexible rate negotiation for per-mile, per-day, overnight, and NoGo fees
- **Trip Management**: Track confirmed trips and job applications
- **Rating System**: Build reputation through 5-star rating system

### For Trucking Companies
- **Pilot Discovery**: Find available pilots on interactive map with real-time locations
- **Job Posting**: Post jobs with pickup/delivery addresses and automatic distance calculation
- **Application Management**: Review pilot applications and negotiate rates
- **Direct Hiring**: Contact pilots directly from the map
- **Trip Tracking**: Monitor active trips and manage job postings
- **Rating System**: Rate pilots after trip completion

### Platform Features
- **Google Maps Integration**: Interactive maps with custom markers and route calculation
- **Email Notifications**: Pilots receive notifications for jobs within their coverage area
- **Automatic Location Expiry**: Pilot locations expire after 48 hours for accuracy
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Rating & Review System**: Mandatory ratings help maintain service quality

## Technology Stack

- **Backend**: Python Flask with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Database**: SQLite (development) / PostgreSQL (production)
- **Maps**: Google Maps JavaScript API, Places API, Directions API
- **Authentication**: Flask-Login for session management
- **Forms**: Flask-WTF with WTForms validation
- **Email**: Flask-Mail for notifications
- **Styling**: Custom CSS with emerald color theme

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- A Google Cloud Platform account for Maps API

### Setup Instructions

1. **Clone or download the project files**

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional but recommended)
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   GOOGLE_MAPS_API_KEY=your-google-maps-api-key
   MAIL_SERVER=smtp.gmail.com
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   DATABASE_URL=sqlite:///app.db
   ```

4. **Initialize the database**
   ```bash
   python app.py
   ```
   The database will be created automatically on first run.

5. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

## Google Maps API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Maps JavaScript API
   - Places API
   - Geocoding API
   - Directions API
4. Create credentials (API Key)
5. Add the API key to your configuration

**Note**: The application includes a demo API key that may have usage limits. For production use, replace with your own API key.

## Application Structure

```
pilots_everywhere4/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── models.py             # Database models
├── forms.py              # WTForms form definitions
├── requirements.txt      # Python dependencies
├── static/               # Static files
│   ├── css/
│   │   └── style.css    # Custom CSS styles
│   ├── js/
│   │   └── main.js      # JavaScript functionality
│   └── images/          # Image assets
├── templates/            # Jinja2 templates
│   ├── base.html        # Base template
│   ├── index.html       # Homepage
│   ├── auth/            # Authentication templates
│   ├── pilot/           # Pilot-specific templates
│   ├── trucking/        # Trucking company templates
│   └── legal/           # Terms and privacy pages
└── Images/              # Reference images
```

## Key Features Implementation

### Location Sharing
- Pilots can share location via GPS or map selection
- Locations automatically expire after 48 hours
- Coverage radius determines job notification area

### Job Marketplace
- Two methods to hire pilots:
  1. Direct contact from map
  2. Job posting with applications
- Rate negotiation with multiple fee types
- Automatic distance calculation

### Rating System
- Mandatory 5-star ratings after trip completion
- Written reviews for detailed feedback
- Aggregate ratings for reputation building

### Payment Structure
- **Currently Free** (Beta period)
- Future pricing:
  - Pilots: $15/month subscription
  - Trucking Companies: $20 per dispatch
- Direct payment between parties (platform doesn't handle money)

## Service Types

1. **Chase Car**: Follows behind the oversize load
2. **Lead Car**: Travels ahead of the oversize load
3. **Height Pole**: Equipped with height-measuring equipment
4. **Steer Car**: Assists with navigation and steering guidance
5. **Route Survey**: Pre-move route surveying service
6. **CEVO**: PA-specific certified escort service

## Development Notes

### Database Models
- User accounts with role-based access (pilot/trucking)
- Profile management for both user types
- Location sharing with expiry
- Job posting and application system
- Trip management and rating system

### Security Features
- Password hashing with Werkzeug
- Session management with Flask-Login
- Form validation and CSRF protection
- Input sanitization and validation

### API Endpoints
- `/api/pilots/locations` - Active pilot locations for trucking companies
- `/api/jobs/active` - Available jobs for pilots
- RESTful design for future mobile app integration

## Customization

### Styling
- Primary color scheme uses emerald theme
- Responsive Bootstrap 5 framework
- Custom CSS variables for easy color changes
- Modern card-based UI design

### Configuration
- Environment-based configuration
- Separate settings for development/production
- Email notification system
- Database flexibility (SQLite/PostgreSQL)

## Contributing

This is a complete marketplace application for the pilot car escort industry. The codebase includes:
- Full user authentication and authorization
- Interactive map integration
- Job posting and application workflows
- Rating and review system
- Email notification system
- Responsive design
- Comprehensive error handling

## Support

For questions or support:
- Email: support@pilotseverywhere.com
- Phone: 1-800-PILOTS-1

## License

Copyright © 2024 Pilots Everywhere. All rights reserved.

---

**Note**: This application is currently in beta. All features are free during the beta period. The platform operates as a marketplace only and does not handle payments between trucking companies and pilots. 