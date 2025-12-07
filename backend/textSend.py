import requests
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()

PLACE_ID = 'ChIJ3VsAyyJFE4cRqvHgchvDkLU'
MAPS_PI_KEY = os.getenv('MAPSAPIKEY')
GENAI_API_KEY = os.getenv('GEMINIKEY')
genai.configure(api_key=GENAI_API_KEY)

def get_place_details(place_id):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,website,price_level,formatted_address,rating&key={MAPS_PI_KEY}"
    response = requests.get(url)
    return response.json()

def generate_place_description(place_data):
    """Takes place JSON and generates text with important info and historical context"""
    
    # Extract key information from the place data
    if place_data.get('status') != 'OK' or 'result' not in place_data:
        return "Error: Could not retrieve place information"
    
    place = place_data['result']
    
    # Prepare the prompt for Gemini
    prompt = f"""Create a brief, engaging description (100-150 words) for someone who is looking at this place. It will appear on their phone screen.

Write 2 short paragraphs:
1. What this place is and why it's significant
2. One interesting historical fact or story about it

Be engaging, and focus on the most fascinating aspect. Make them feel like they discovered something special.

Make sure to search the internet for real historical information about the place.

Here is the complete place data in JSON format:
{json.dumps(place, indent=2)}

Keep it short, interesting, and mobile-friendly."""

    # Initialize the model
    model = genai.GenerativeModel('gemini-2.5-flash')    
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