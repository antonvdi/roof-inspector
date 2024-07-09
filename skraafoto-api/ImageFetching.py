import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
from BoundingBoxFetching import AddressNotFoundError, get_bounding_box_for_address, get_coordinates_for_address
from DatafordelerFetching import get_building_from_address, get_height_from_model, get_matrikel_from_address
import os
from dotenv import load_dotenv
from Utils import convert_coordinates
from ComputerVisionHandler import draw_polygon
import pandas as pd

load_dotenv()

DATAFORSYNING_TOKEN = os.getenv('DATAFORSYNING_TOKEN') 

def calculate_point_on_image(item, x, y, z=10):
    """Calculates the pixel coordinates of a given point in a given image.
    Returns a tuple with the pixel coordinates. x y and z must be in EPSG:25832."""

    props = item["properties"]

    m11, m12, m13, m21, m22, m23, m31, m32, m33 = props["pers:rotation_matrix"]
    Xc, Yc, Zc = props["pers:perspective_center"]

    f_mm = props["pers:interior_orientation"]["focal_length"]
    ppo_x, ppo_y = props["pers:interior_orientation"]["principal_point_offset"]
    pixel_size = props["pers:interior_orientation"]["pixel_spacing"][0]
    sensor_cols, sensor_rows = props["pers:interior_orientation"]["sensor_array_dimensions"]

    f = f_mm / pixel_size
    x0 = sensor_cols * 0.5 + ppo_x / pixel_size
    y0 = sensor_rows * 0.5 + ppo_y / pixel_size

    dX = (x-Xc)
    dY = (y-Yc)
    dZ = (z-Zc)

    n = (m31 * dX + m32 * dY + m33 * dZ)

    xa = x0 - f * (m11 * dX + m12 * dY + m13 * dZ) / n
    ya = y0 - f * (m21 * dX + m22 * dY + m23 * dZ) / n

    #convert origo to upper left
    ya_upper_left = sensor_rows - ya

    return (xa, ya_upper_left)


def get_metadata(item, coords):
    """Calculates the pixel coordinates of a given address in a given image.
    Returns a tuple with the pixel coordinates."""
    
    wgs84_coords = convert_coordinates(coords[0], coords[1], "EPSG:"+str(item["properties"]["pers:crs"]))
    X, Y = wgs84_coords
    Z = 10

    return calculate_point_on_image(item, X, Y, Z)

def get_matrikel_geometry_on_image(coords, item):
    """Returns the geometry of the matrikel."""
    #print(coords)
    
    points_on_image = [calculate_point_on_image(item, coord[0], coord[1], coord[2]) for coord in coords]

    return points_on_image

def get_matrikel_coordinates(matrikel):
    """Returns the coordinates of the matrikel."""
    coordinates = matrikel["features"][0]["geometry"]["coordinates"]
    crs = matrikel["features"][0]["geometry"]["crs"]["properties"]["name"]
    
    epsg_25832_coords = [convert_coordinates(coord[0], coord[1], "EPSG:25832", crs) for coord in coordinates[0]]
    epsg_25832_coords_with_height = [(coord[0], coord[1], get_height_from_model(coord[0], coord[1])) for coord in epsg_25832_coords]
    
    return epsg_25832_coords_with_height

def get_building_coordinates(building):
    """Returns the coordinates of the building."""
    polygon_data = building["wfs:FeatureCollection"]["wfs:member"]["gdk60:Bygning"]["gdk60:geometri"]["gml:Polygon"]
    coordinates = polygon_data["gml:exterior"]["gml:LinearRing"]["gml:posList"]["#text"]
    coordinates = coordinates.split(" ")
    coordinates = [(float(coordinates[i]), float(coordinates[i+1]), float(coordinates[i+2])) for i in range(0, len(coordinates), 3)]
    return coordinates

def fetch_images(address, token):
    """Fetches images from the Skraafoto API for a given address.
    Returns a list of tuples with the image data and the pixel coordinates of the address.
    """
    bbox = get_bounding_box_for_address(address)
    #matrikel_data = get_matrikel_from_address(address)
    #matrikel_coords = get_matrikel_coordinates(matrikel_data)
    building = get_building_from_address(address)
    matrikel_coords = get_building_coordinates(building)

    #collections = ["skraafotos2017", "skraafotos2019", "skraafotos2022"]
    collections = ["skraafotos2019"]
    directions = ["north", "east", "south", "west"]
    base_url = "https://api.dataforsyningen.dk/rest/skraafoto_api/v1.0/collections/"
    headers = {
        "token": token,
        "Content-Type": "application/geo+json"
    }

    images = []

    for collection in collections:
        for direction in directions:
            url = (f"{base_url}{collection}/items?limit=1&bbox={bbox}"
                   f"&bbox-crs=http://www.opengis.net/def/crs/OGC/1.3/CRS84"
                   f"&crs=http://www.opengis.net/def/crs/OGC/1.3/CRS84"
                   f"&filter-lang=cql-json&filter={{\"eq\": [{{\"property\": \"direction\"}}, \"{direction}\"]}}")
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                response_json = response.json()
                if response_json["features"]:
                    image_url = response_json["features"][0]["assets"]["data"]["href"]

                    metadata = {
                        "points": get_matrikel_geometry_on_image(matrikel_coords, response_json["features"][0]),
                        "pixel_size": response_json["features"][0]["properties"]["pers:interior_orientation"]["pixel_spacing"][0]
                    }

                    image_response = requests.get(image_url, headers=headers)

                    if image_response.status_code == 200:
                        images.append((image_response.content, metadata))
                    else:
                        print(f"Failed to fetch the image data from {image_url}")
            else:
                print(f"Failed to fetch metadata from {url}")

    return images if images else None
    
def convert_tiff_to_jpg(image):
    """Converts a tiff image to a jpeg image."""
    jpeg_image = image.convert("RGB")
    return jpeg_image

def save_image(image, path, suffix=""):
    """Saves an image to a given path with a given suffix."""
    # if path is not set, make the path /output/image_<CURRENT TIME AND DATE>.jpg
    if path == None:
        path = "output/image_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + suffix + ".jpg"
    else:
        path = path + "_" + suffix + ".jpg"
    image.save(path)

def save_metadata(metadata, path):
    """Saves metadata to a given path."""
    if metadata:
        with open(path + ".csv", "a") as file:
            file.write(metadata)

def get_and_save_images(address, token=DATAFORSYNING_TOKEN, path=None):
    """Fetches and saves images along with metadata with polygon for building for a given address."""
    image_tuples = fetch_images(address, token)

    if image_tuples == None:
        return
    
    i = 0
    metadata_str = "image_id,x,y,pixel_size\n"
    
    save_metadata(metadata_str, path)
    for image, metadata in image_tuples:
        my_image = Image.open(BytesIO(image)) 

        jpeg = convert_tiff_to_jpg(my_image)
        save_image(jpeg, path, str(i))
        
        metadata_str = "\n".join([str(i)+","+str(metadata_item[0])+","+str(metadata_item[1])+","+str(metadata["pixel_size"]) for metadata_item in metadata["points"]])+"\n"
        save_metadata(metadata_str, path)
        i += 1

def get_and_save_processed_images(address, token=DATAFORSYNING_TOKEN, path=None):
    """Fetches and saves cropped images of the building for a given address."""
    try: 
        image_tuples = fetch_images(address, token)
    except AddressNotFoundError:
        return
    
    i = 0
    
    for image, metadata in image_tuples:
        my_image = Image.open(BytesIO(image)) 
        jpeg = convert_tiff_to_jpg(my_image)

        image = draw_polygon(jpeg, metadata["points"], metadata["pixel_size"])
        save_image(image, path, str(i))
        i += 1

# Load addresses from Excel file
addresses_df = pd.read_excel('adresser.xlsx')
addresses = addresses_df['Adresse'] + ', ' + addresses_df['Postnummer'].astype(str) + " " + addresses_df['By']

# Iterate over addresses and call get_and_save_processed_images
for address in addresses:
    get_and_save_processed_images(address, DATAFORSYNING_TOKEN, "output2/" + address.replace(" ", ""))

# Example usage
#get_and_save_processed_images("Valdemarsgade 43, 4760 Vordingborg", DATAFORSYNING_TOKEN, "output2/valdemarsgade43")
