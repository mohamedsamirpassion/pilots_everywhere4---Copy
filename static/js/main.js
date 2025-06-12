// Global variables
let map;
let markers = [];
let userLocationMarker;
let tempLocationMarker;
let isSelectingLocation = false;
let autocompletePickup;
let autocompleteDelivery;

// Initialize Google Maps
function initMap() {
    // Default center (middle of North America)
    const defaultCenter = { lat: 39.8283, lng: -98.5795 };
    
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 4,
        center: defaultCenter,
        styles: [
            {
                featureType: "poi",
                elementType: "labels",
                stylers: [{ visibility: "off" }]
            }
        ]
    });

    // Initialize autocomplete if elements exist
    initAutocomplete();
    
    // Load map data based on current page
    const currentPage = window.location.pathname;
    
    if (currentPage.includes('dashboard')) {
        loadMapData();
    }
    
    // Set up map click handler for location selection
    if (document.getElementById('location-select-btn')) {
        setupLocationSelection();
    }
}

// Initialize Google Places Autocomplete
function initAutocomplete() {
    const pickupInput = document.getElementById('pickup_address');
    const deliveryInput = document.getElementById('delivery_address');
    
    if (pickupInput) {
        autocompletePickup = new google.maps.places.Autocomplete(pickupInput, {
            types: ['address'],
            componentRestrictions: { country: ['us', 'ca'] }
        });
        
        autocompletePickup.addListener('place_changed', function() {
            const place = autocompletePickup.getPlace();
            if (place.geometry) {
                document.getElementById('pickup_latitude').value = place.geometry.location.lat();
                document.getElementById('pickup_longitude').value = place.geometry.location.lng();
                
                // Calculate distance if delivery is also set
                calculateDistance();
            }
        });
    }
    
    if (deliveryInput) {
        autocompleteDelivery = new google.maps.places.Autocomplete(deliveryInput, {
            types: ['address'],
            componentRestrictions: { country: ['us', 'ca'] }
        });
        
        autocompleteDelivery.addListener('place_changed', function() {
            const place = autocompleteDelivery.getPlace();
            if (place.geometry) {
                document.getElementById('delivery_latitude').value = place.geometry.location.lat();
                document.getElementById('delivery_longitude').value = place.geometry.location.lng();
                
                // Calculate distance if pickup is also set
                calculateDistance();
            }
        });
    }
}

// Load map data (pilots and jobs)
function loadMapData() {
    // Load pilots
    fetch('/api/pilots/locations')
        .then(response => response.json())
        .then(pilots => {
            pilots.forEach(pilot => {
                addPilotMarker(pilot);
            });
        })
        .catch(error => console.error('Error loading pilots:', error));
    
    // Load jobs
    fetch('/api/jobs/active')
        .then(response => response.json())
        .then(jobs => {
            jobs.forEach(job => {
                addJobMarker(job);
            });
        })
        .catch(error => console.error('Error loading jobs:', error));
}

// Add pilot marker to map
function addPilotMarker(pilot) {
    const marker = new google.maps.Marker({
        position: { lat: pilot.latitude, lng: pilot.longitude },
        map: map,
        title: pilot.company_name,
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: '#059669',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 2,
            scale: 15
        }
    });
    
    // Create info window
    const infoWindow = new google.maps.InfoWindow({
        content: createPilotInfoContent(pilot)
    });
    
    marker.addListener('click', function() {
        // Close other info windows
        markers.forEach(m => {
            if (m.infoWindow) {
                m.infoWindow.close();
            }
        });
        
        infoWindow.open(map, marker);
    });
    
    marker.infoWindow = infoWindow;
    markers.push(marker);
}

// Add job marker to map
function addJobMarker(job) {
    const marker = new google.maps.Marker({
        position: { lat: job.pickup_latitude, lng: job.pickup_longitude },
        map: map,
        title: `Job: ${job.pickup_address}`,
        icon: {
            path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
            fillColor: '#065f46',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 2,
            scale: 8
        }
    });
    
    const infoWindow = new google.maps.InfoWindow({
        content: createJobInfoContent(job)
    });
    
    marker.addListener('click', function() {
        // Close other info windows
        markers.forEach(m => {
            if (m.infoWindow) {
                m.infoWindow.close();
            }
        });
        
        infoWindow.open(map, marker);
    });
    
    marker.infoWindow = infoWindow;
    markers.push(marker);
}

// Create pilot info window content
function createPilotInfoContent(pilot) {
    const services = pilot.services ? pilot.services.join(', ') : 'N/A';
    const rating = pilot.rating ? createStarRating(pilot.rating) : 'No ratings yet';
    
    return `
        <div class="p-3" style="max-width: 300px;">
            <h6 class="fw-bold text-emerald">${pilot.company_name}</h6>
            <p class="mb-1"><strong>Contact:</strong> ${pilot.contact_name}</p>
            <p class="mb-1"><strong>Services:</strong> ${services}</p>
            <p class="mb-2"><strong>Rating:</strong> ${rating}</p>
            <div class="d-flex gap-2">
                <button class="btn btn-sm btn-emerald" onclick="viewPilotProfile(${pilot.id})">
                    View Profile
                </button>
                <button class="btn btn-sm btn-outline-emerald" onclick="offerJob(${pilot.id})">
                    Offer Job
                </button>
            </div>
        </div>
    `;
}

// Create job info window content
function createJobInfoContent(job) {
    const services = job.services_required ? job.services_required.join(', ') : 'N/A';
    const rates = [];
    
    if (job.rate_per_mile) rates.push(`$${job.rate_per_mile}/mile`);
    if (job.rate_per_day) rates.push(`$${job.rate_per_day}/day`);
    if (job.overnight_rate) rates.push(`$${job.overnight_rate}/overnight`);
    
    const rateText = rates.length > 0 ? rates.join(', ') : 'Rate negotiable';
    
    return `
        <div class="p-3" style="max-width: 300px;">
            <h6 class="fw-bold text-emerald">Job Available</h6>
            <p class="mb-1"><strong>From:</strong> ${job.pickup_address}</p>
            <p class="mb-1"><strong>To:</strong> ${job.delivery_address}</p>
            <p class="mb-1"><strong>Pickup:</strong> ${new Date(job.pickup_datetime).toLocaleDateString()}</p>
            <p class="mb-1"><strong>Services:</strong> ${services}</p>
            <p class="mb-1"><strong>Rate:</strong> ${rateText}</p>
            <p class="mb-2"><strong>Distance:</strong> ${job.distance_miles} miles</p>
            <div class="d-flex gap-2">
                <button class="btn btn-sm btn-emerald" onclick="viewJobDetails(${job.id})">
                    View Details
                </button>
                <button class="btn btn-sm btn-outline-emerald" onclick="applyForJob(${job.id})">
                    Apply
                </button>
            </div>
        </div>
    `;
}

// Create star rating display
function createStarRating(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    let stars = '';
    
    for (let i = 0; i < fullStars; i++) {
        stars += '<i class="fas fa-star text-warning"></i>';
    }
    
    if (hasHalfStar) {
        stars += '<i class="fas fa-star-half-alt text-warning"></i>';
    }
    
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    for (let i = 0; i < emptyStars; i++) {
        stars += '<i class="far fa-star text-warning"></i>';
    }
    
    return `${stars} (${rating.toFixed(1)})`;
}

// Location selection functionality
function setupLocationSelection() {
    const selectBtn = document.getElementById('location-select-btn');
    const useGpsBtn = document.getElementById('use-gps-btn');
    
    if (selectBtn) {
        selectBtn.addEventListener('click', function() {
            toggleLocationSelection();
        });
    }
    
    if (useGpsBtn) {
        useGpsBtn.addEventListener('click', function() {
            getCurrentLocation();
        });
    }
}

// Toggle location selection mode
function toggleLocationSelection() {
    const selectBtn = document.getElementById('location-select-btn');
    
    if (!isSelectingLocation) {
        isSelectingLocation = true;
        selectBtn.textContent = 'Cancel Selection';
        selectBtn.className = 'btn btn-warning';
        map.setOptions({ draggableCursor: 'crosshair' });
        
        // Add click listener
        map.addListener('click', onMapClick);
        
        showToast('Click anywhere on the map to select your location', 'info');
    } else {
        cancelLocationSelection();
    }
}

// Handle map click for location selection
function onMapClick(event) {
    if (!isSelectingLocation) return;
    
    const lat = event.latLng.lat();
    const lng = event.latLng.lng();
    
    // Remove existing temp marker
    if (tempLocationMarker) {
        tempLocationMarker.setMap(null);
    }
    
    // Add temporary marker
    tempLocationMarker = new google.maps.Marker({
        position: { lat: lat, lng: lng },
        map: map,
        draggable: true,
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: '#f59e0b',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 2,
            scale: 12
        }
    });
    
    // Update form fields
    document.getElementById('latitude').value = lat;
    document.getElementById('longitude').value = lng;
    
    // Reverse geocode to get address
    reverseGeocode(lat, lng);
    
    // Show confirmation
    showLocationConfirmation(lat, lng);
}

// Cancel location selection
function cancelLocationSelection() {
    isSelectingLocation = false;
    const selectBtn = document.getElementById('location-select-btn');
    selectBtn.textContent = 'Select on Map';
    selectBtn.className = 'btn btn-outline-emerald';
    map.setOptions({ draggableCursor: null });
    
    // Remove temp marker
    if (tempLocationMarker) {
        tempLocationMarker.setMap(null);
        tempLocationMarker = null;
    }
    
    // Remove click listener
    google.maps.event.clearListeners(map, 'click');
}

// Get current GPS location
function getCurrentLocation() {
    if (!navigator.geolocation) {
        showToast('Geolocation is not supported by this browser', 'error');
        return;
    }
    
    const gpsBtn = document.getElementById('use-gps-btn');
    gpsBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting Location...';
    gpsBtn.disabled = true;
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            
            // Update form fields
            document.getElementById('latitude').value = lat;
            document.getElementById('longitude').value = lng;
            
            // Center map on location
            map.setCenter({ lat: lat, lng: lng });
            map.setZoom(12);
            
            // Add marker
            if (userLocationMarker) {
                userLocationMarker.setMap(null);
            }
            
            userLocationMarker = new google.maps.Marker({
                position: { lat: lat, lng: lng },
                map: map,
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    fillColor: '#059669',
                    fillOpacity: 1,
                    strokeColor: '#ffffff',
                    strokeWeight: 2,
                    scale: 12
                }
            });
            
            // Reverse geocode
            reverseGeocode(lat, lng);
            
            gpsBtn.innerHTML = '<i class="fas fa-crosshairs"></i> Use GPS Location';
            gpsBtn.disabled = false;
            
            showToast('Location found successfully!', 'success');
        },
        function(error) {
            let message = 'Unable to retrieve your location';
            
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    message = 'Location access denied by user';
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = 'Location information unavailable';
                    break;
                case error.TIMEOUT:
                    message = 'Location request timed out';
                    break;
            }
            
            showToast(message, 'error');
            
            gpsBtn.innerHTML = '<i class="fas fa-crosshairs"></i> Use GPS Location';
            gpsBtn.disabled = false;
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000
        }
    );
}

// Reverse geocode coordinates to address
function reverseGeocode(lat, lng) {
    const geocoder = new google.maps.Geocoder();
    const latlng = { lat: lat, lng: lng };
    
    geocoder.geocode({ location: latlng }, function(results, status) {
        if (status === 'OK' && results[0]) {
            const address = results[0].formatted_address;
            document.getElementById('address').value = address;
        }
    });
}

// Show location confirmation modal
function showLocationConfirmation(lat, lng) {
    // Implementation depends on whether you want a modal or inline confirmation
    // For now, we'll just show a toast
    showToast('Location selected! You can drag the marker to adjust.', 'success');
}

// Calculate distance between pickup and delivery
function calculateDistance() {
    const pickupLat = document.getElementById('pickup_latitude').value;
    const pickupLng = document.getElementById('pickup_longitude').value;
    const deliveryLat = document.getElementById('delivery_latitude').value;
    const deliveryLng = document.getElementById('delivery_longitude').value;
    
    if (pickupLat && pickupLng && deliveryLat && deliveryLng) {
        const service = new google.maps.DistanceMatrixService();
        
        service.getDistanceMatrix({
            origins: [{ lat: parseFloat(pickupLat), lng: parseFloat(pickupLng) }],
            destinations: [{ lat: parseFloat(deliveryLat), lng: parseFloat(deliveryLng) }],
            travelMode: google.maps.TravelMode.DRIVING,
            unitSystem: google.maps.UnitSystem.IMPERIAL,
            avoidHighways: false,
            avoidTolls: false
        }, function(response, status) {
            if (status === 'OK') {
                const distance = response.rows[0].elements[0].distance;
                if (distance) {
                    const miles = Math.round(distance.value / 1609.34); // Convert meters to miles
                    const distanceDisplay = document.getElementById('distance-display');
                    if (distanceDisplay) {
                        distanceDisplay.textContent = `Distance: ${miles} miles`;
                        distanceDisplay.style.display = 'block';
                    }
                }
            }
        });
    }
}

// Utility functions
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 100px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
}

// View pilot profile
function viewPilotProfile(pilotId) {
    window.open(`/pilot/profile/${pilotId}`, '_blank');
}

// Offer job to pilot
function offerJob(pilotId) {
    window.location.href = `/trucking/offer-job/${pilotId}`;
}

// View job details
function viewJobDetails(jobId) {
    window.open(`/job/${jobId}`, '_blank');
}

// Apply for job
function applyForJob(jobId) {
    window.location.href = `/pilot/apply/${jobId}`;
}

// Filter functions
function filterPilots() {
    const serviceFilter = document.getElementById('service-filter');
    const radiusFilter = document.getElementById('radius-filter');
    const ratingFilter = document.getElementById('rating-filter');
    
    if (serviceFilter || radiusFilter || ratingFilter) {
        const filters = {
            service: serviceFilter ? serviceFilter.value : '',
            radius: radiusFilter ? radiusFilter.value : '',
            rating: ratingFilter ? ratingFilter.value : ''
        };
        
        // Clear existing markers
        clearMarkers();
        
        // Load filtered data
        loadFilteredPilots(filters);
    }
}

function filterJobs() {
    const serviceFilter = document.getElementById('job-service-filter');
    const radiusFilter = document.getElementById('job-radius-filter');
    const rateFilter = document.getElementById('job-rate-filter');
    
    if (serviceFilter || radiusFilter || rateFilter) {
        const filters = {
            service: serviceFilter ? serviceFilter.value : '',
            radius: radiusFilter ? radiusFilter.value : '',
            rate: rateFilter ? rateFilter.value : ''
        };
        
        // Clear existing markers
        clearMarkers();
        
        // Load filtered data
        loadFilteredJobs(filters);
    }
}

function clearMarkers() {
    markers.forEach(marker => {
        marker.setMap(null);
    });
    markers = [];
}

function loadFilteredPilots(filters) {
    const params = new URLSearchParams(filters);
    
    fetch(`/api/pilots/locations?${params}`)
        .then(response => response.json())
        .then(pilots => {
            pilots.forEach(pilot => {
                addPilotMarker(pilot);
            });
        })
        .catch(error => console.error('Error loading filtered pilots:', error));
}

function loadFilteredJobs(filters) {
    const params = new URLSearchParams(filters);
    
    fetch(`/api/jobs/active?${params}`)
        .then(response => response.json())
        .then(jobs => {
            jobs.forEach(job => {
                addJobMarker(job);
            });
        })
        .catch(error => console.error('Error loading filtered jobs:', error));
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set up filter event listeners
    const serviceFilter = document.getElementById('service-filter');
    const radiusFilter = document.getElementById('radius-filter');
    const ratingFilter = document.getElementById('rating-filter');
    const jobServiceFilter = document.getElementById('job-service-filter');
    const jobRadiusFilter = document.getElementById('job-radius-filter');
    const jobRateFilter = document.getElementById('job-rate-filter');
    
    if (serviceFilter) serviceFilter.addEventListener('change', filterPilots);
    if (radiusFilter) radiusFilter.addEventListener('change', filterPilots);
    if (ratingFilter) ratingFilter.addEventListener('change', filterPilots);
    if (jobServiceFilter) jobServiceFilter.addEventListener('change', filterJobs);
    if (jobRadiusFilter) jobRadiusFilter.addEventListener('change', filterJobs);
    if (jobRateFilter) jobRateFilter.addEventListener('change', filterJobs);
}); 