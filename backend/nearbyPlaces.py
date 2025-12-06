import requests
import math
import time
TEST_COORD={
    "latitude": 38.860180,
    "longitude":  -104.802557
}

API_KEY = "AIzaSyCxUpksy_CDTlSJZ6eh4oCgFpULvT3P8yA"
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    d_lon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    
    y = math.sin(d_lon) * math.cos(lat2_rad)
    x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lon))
    
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360  # Normalize to 0-360

def angle_difference(heading, bearing):
    diff = abs(heading - bearing)
    if diff > 180:
        diff = 360 - diff
    return diff

def get_nearby_places(latitude, longitude, radius=300):
    all_results = []
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={latitude},{longitude}&radius={radius}&key={API_KEY}"
    
    # Get first page
    response = requests.get(url)
    data = response.json()
    
    if data.get('status') == 'OK' and 'results' in data:
        all_results.extend(data['results'])
        
        # Get additional pages if available (up to 3 pages = 60 results total)
        next_page_token = data.get('next_page_token')
        page_count = 0
        max_pages = 2  # Can get up to 3 pages total (20 + 20 + 20 = 60 results)
        
        while next_page_token and page_count < max_pages:
            # Wait a bit for token to become valid (Google requires a short delay)
            time.sleep(2)
            
            url_next = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?pagetoken={next_page_token}&key={API_KEY}"
            response_next = requests.get(url_next)
            data_next = response_next.json()
            
            if data_next.get('status') == 'OK' and 'results' in data_next:
                all_results.extend(data_next['results'])
                next_page_token = data_next.get('next_page_token')
                page_count += 1
            else:
                break
    
    # Filter results to only include places actually within the radius
    # (API radius can sometimes return places slightly outside)
    filtered_results = []
    for place in all_results:
        place_lat = place['geometry']['location']['lat']
        place_lng = place['geometry']['location']['lng']
        distance = calculate_distance(latitude, longitude, place_lat, place_lng)
        
        if distance <= radius:
            filtered_results.append(place)
    
    # Return combined results in the same format as original API response
    return {
        'status': 'OK',
        'results': filtered_results
    }

def sort_places_by_distance(json_data, user_lat, user_lng):
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

def calculate_likelihood(angle_difference, distance, max_distance, fov=45):
    # Filter out buildings outside FOV
    if angle_difference > fov:
        return None
    
    # Normalize angle difference (0-1, where 0 is perfect alignment)
    heading_score = angle_difference / fov
    
    # Normalize distance (0-1, where 0 is closest)
    distance_score = distance / max_distance if max_distance > 0 else 0
    
    # Calculate likelihood: 85% heading, 15% distance (lower is better)
    likelihood = (heading_score * 0.85) + (distance_score * 0.15)
    
    return likelihood

def rank_places_by_heading(json_data, user_lat, user_lng, heading, max_distance=1000):
    places_list = []
    FOV = 45  # Field of view in degrees
    
    if json_data.get('status') == 'OK' and 'results' in json_data:
        # First pass: collect valid places and find max distance
        valid_places = []
        max_dist = 0
        
        for place in json_data['results']:
            place_lat = place['geometry']['location']['lat']
            place_lng = place['geometry']['location']['lng']
            distance = calculate_distance(user_lat, user_lng, place_lat, place_lng)
            
            # Skip if too far
            if distance > max_distance:
                continue
            
            # Calculate bearing from user to place
            bearing = calculate_bearing(user_lat, user_lng, place_lat, place_lng)
            
            # Calculate angle difference from heading
            angle_diff = angle_difference(heading, bearing)
            
            # Only include places within FOV
            if angle_diff <= FOV:
                valid_places.append({
                    'name': place.get('name', 'Unknown'),
                    'lat': place_lat,
                    'lng': place_lng,
                    'distance': distance,
                    'bearing': bearing,
                    'angle_difference': angle_diff
                })
                max_dist = max(max_dist, distance)
        
        # Second pass: calculate likelihood scores
        for place in valid_places:
            likelihood = calculate_likelihood(
                place['angle_difference'],
                place['distance'],
                max_dist,
                FOV
            )
            
            if likelihood is not None:
                places_list.append({
                    'name': place['name'],
                    'distance': round(place['distance'], 2),
                    'bearing': round(place['bearing'], 2),
                    'angle_difference': round(place['angle_difference'], 2),
                    'likelihood': round(likelihood, 4)
                })
        
        # Sort by likelihood (lower is better)
        places_list.sort(key=lambda x: x['likelihood'])
    
    return places_list

# Example usage
if __name__ == "__main__":
    # Get all buildings within 300 meters with pagination
    json_response = get_nearby_places(TEST_COORD["latitude"], TEST_COORD["longitude"], radius=300)
    print(f"Total buildings found within 300m: {len(json_response.get('results', []))}\n")
    
    # Example: Sort by distance only
    sorted_places = sort_places_by_distance(json_response, TEST_COORD["latitude"], TEST_COORD["longitude"])
    print("Places sorted by distance:")
    print(sorted_places)
    print("\n" + "="*50 + "\n")
    
    # Example: Rank by heading (camera pointing North)
    heading = 180  # North (0 degrees)
    ranked_places = rank_places_by_heading(
        json_response, 
        TEST_COORD["latitude"], 
        TEST_COORD["longitude"], 
        heading,
        max_distance=1000
    )
    print(f"Places ranked by heading ({heading}° - North), filtered by 45° FOV:")
    for i, place in enumerate(ranked_places, 1):
        print(f"{i}. {place['name']}")
        print(f"   Distance: {place['distance']}m")
        print(f"   Bearing: {place['bearing']}°")
        print(f"   Angle from heading: {place['angle_difference']}°")