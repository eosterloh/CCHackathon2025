import requests
import google.generativeai as genai
import json
PLACE_ID = 'ChIJ3VsAyyJFE4cRqvHgchvDkLU'
MAPS_PI_KEY = "AIzaSyCxUpksy_CDTlSJZ6eh4oCgFpULvT3P8yA"
GENAI_API_KEY = ""
genai.configure(api_key=GEMINI_API_KEY)

def get_place_details(place_id):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,website,price_level,rating&key={MAPS_PI_KEY}"
    response = requests.get(url)
    return response.json()

def generate_place_description(place_data):
    """Takes place JSON and generates text with important info and historical context"""
    
    # Extract key information from the place data
    if place_data.get('status') != 'OK' or 'result' not in place_data:
        return "Error: Could not retrieve place information"
    
    place = place_data['result']
    
    # Prepare the prompt for Gemini
    prompt = f"""Based on the following information about a place, provide:
1. Important information about this place (what it is, what it offers)
2. Historical context and significance (if it's a historical building or landmark)
3. Why someone should visit it

Place Information:
- Name: {place.get('name', 'Unknown')}
- Address: {place.get('formatted_address', 'Unknown')}
- Rating: {place.get('rating', 'N/A')}/5
- Types: {', '.join(place.get('types', []))}
- Phone: {place.get('formatted_phone_number', 'Not available')}
- Website: {place.get('website', 'Not available')}
- Opening Hours: {json.dumps(place.get('opening_hours', {}), indent=2) if place.get('opening_hours') else 'Not available'}

Please provide a comprehensive description that includes both practical information and historical context if applicable. Make it engaging and informative."""

    # Initialize the model
    model = genai.GenerativeModel('gemini-pro')
    
    # Generate response
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating description: {str(e)}"

def get_place_with_description(place_id):
    """Get place details and generate description"""
    place_data = get_place_details(place_id)
    description = generate_place_description(place_data)
    
    return {
        'place_data': place_data,
        'description': description
    }


result = get_place_with_description(PLACE_ID)
print("=== Place Data ===")
print(json.dumps(result['place_data'], indent=2))
print("\n=== Generated Description ===")
print(result['description'])