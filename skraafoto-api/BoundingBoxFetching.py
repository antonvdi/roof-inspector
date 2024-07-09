import requests

def get_coordinates_for_address(address):
    # Step 1: Geocode the Address
    geocode_url = f"https://api.dataforsyningen.dk/adresser?q={address}"
    response = requests.get(geocode_url)
    data = response.json()

    if not data:
        return {"error": "Address not found."}

    # Extract the coordinates
    coordinates = data[0]['adgangsadresse']['adgangspunkt']['koordinater']
    lon, lat = coordinates[0], coordinates[1]
    return (lon, lat)

def get_address_object(address):
    # Step 1: Geocode the Address
    geocode_url = f"https://api.dataforsyningen.dk/adresser?q={address}"
    response = requests.get(geocode_url)
    data = response.json()

    if not data:
        return {"error": "Address not found."}
        
    return data[0]

def get_bounding_box_for_address(address, buffer=0.0001):
    lon, lat = get_coordinates_for_address(address)

    # Step 2: Determine the Bounding Box with a buffer
    min_lon = lon - buffer
    min_lat = lat - buffer
    max_lon = lon + buffer
    max_lat = lat + buffer

    # Form the bbox
    bbox = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    return bbox
