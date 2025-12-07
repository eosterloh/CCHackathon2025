from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import base64
import json
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from backend.textSend import get_place_with_description, get_place_details
from backend.nearbyPlaces import get_nearby_places, rank_places_by_heading

load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow requests from mobile app

# Configuration for file uploads
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/identify-place', methods=['POST'])
def identify_place():
    """
    Receives coordinates, azimuth (heading), and image from phone.
    Returns place description, image, and place details.
    
    Expected request format:
    - Form data with:
      * latitude (float)
      * longitude (float) 
      * azimuth (float) - heading/direction phone is pointing
      * image (file) - image of what user is looking at
    
    OR JSON with base64 encoded image:
    {
      "latitude": 38.831013,
      "longitude": -104.823753,
      "azimuth": 180,
      "image": "base64_encoded_image_string"
    }
    """
    try:
        # Handle form-data (multipart/form-data)
        if request.files:
            latitude = float(request.form.get('latitude'))
            longitude = float(request.form.get('longitude'))
            azimuth = float(request.form.get('azimuth'))
            image_file = request.files.get('image')
            
            # Save and encode image
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(filepath)
                
                # Read image as base64 for response
                with open(filepath, 'rb') as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                
                # Optionally clean up file
                # os.remove(filepath)
                
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid or missing image file'
                }), 400
        
        # Handle JSON with base64 image
        elif request.is_json:
            data = request.json
            latitude = float(data.get('latitude'))
            longitude = float(data.get('longitude'))
            azimuth = float(data.get('azimuth'))
            image_base64 = data.get('image', '')  # Already base64 encoded
        
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid request format. Send form-data or JSON with image.'
            }), 400
        
        # Find nearby places using coordinates and azimuth
        places_response = get_nearby_places(latitude, longitude, radius=300)
        
        # Rank places by heading (azimuth) - most likely place user is looking at
        ranked_places = rank_places_by_heading(
            places_response, 
            latitude, 
            longitude, 
            azimuth,
            max_distance=1000
        )
        
        if not ranked_places:
            return jsonify({
                'status': 'no_places',
                'message': 'No places found nearby',
                'image': image_base64  # Return image even if no place found
            })
        
        # Get the top ranked place (most likely match)
        top_place = ranked_places[0]
        
        # Find the full place details and place_id
        place_id = None
        full_place_data = None
        for place in places_response.get('results', []):
            if place.get('name') == top_place['name']:
                place_id = place.get('place_id')
                full_place_data = place
                break
        
        if not place_id:
            return jsonify({
                'status': 'error',
                'message': 'Could not find place ID',
                'image': image_base64
            }), 500
        
        # Get place description using AI
        place_info = get_place_with_description(place_id)
        place_data = place_info['place_data']['result']
        description = place_info['description']
        
        # Prepare response with all relevant data
        response_data = {
            'status': 'success',
            'place': {
                'place_id': place_id,
                'name': place_data.get('name'),
                'description': description,
                'address': place_data.get('formatted_address', ''),
                'rating': place_data.get('rating'),
                'website': place_data.get('website'),
                'distance': top_place['distance'],  # meters
                'bearing': top_place.get('bearing'),
                'likelihood_score': top_place.get('likelihood')
            },
            'image': image_base64,  # Return the image back
            'location': {
                'latitude': latitude,
                'longitude': longitude,
                'azimuth': azimuth
            },
            'photo_reference': full_place_data.get('photos', [{}])[0].get('photo_reference') if full_place_data else None
        }
        
        return jsonify(response_data)
    
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': f'Invalid coordinate or azimuth value: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/place/<place_id>', methods=['GET'])
def get_place(place_id):
    """Get place details with AI description"""
    result = get_place_with_description(place_id)
    return jsonify(result)

@app.route('/api/nearby', methods=['GET'])
def nearby():
    """Get nearby places ranked by heading"""
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))
    heading = float(request.args.get('heading', 0))
    
    places = get_nearby_places(lat, lng)
    ranked = rank_places_by_heading(places, lat, lng, heading)
    return jsonify(ranked)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)