import requests
import math
TEST_COORD={
    "latitude": 38.831013,
    "longitude": -104.823753
}

API_KEY = "AIzaSyCxUpksy_CDTlSJZ6eh4oCgFpULvT3P8yA"
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in meters using Haversine formula"""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def get_nearby_places(latitude, longitude):
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={latitude},{longitude}&radius=500&key={API_KEY}"
    response = requests.get(url)
    return response.json()

def sort_places_by_distance(json_data, user_lat, user_lng):
    """Takes JSON response and returns a list of places ordered by distance"""
    places_list = []
    
    if json_data.get('status') == 'OK' and 'results' in json_data:
        for place in json_data['results']:
            place_lat = place['geometry']['location']['lat']
            place_lng = place['geometry']['location']['lng']
            distance = calculate_distance(user_lat, user_lng, place_lat, place_lng)
            
            places_list.append({
                'name': place.get('name', 'Unknown'),
                'distance': round(distance, 2)  # Distance in meters
            })
        
        # Sort by distance (closest first)
        places_list.sort(key=lambda x: x['distance'])
    
    return places_list

# Example usage
json_response = get_nearby_places(TEST_COORD["latitude"], TEST_COORD["longitude"])
sorted_places = sort_places_by_distance(json_response, TEST_COORD["latitude"], TEST_COORD["longitude"])
print(sorted_places)