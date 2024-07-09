import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
from BoundingBoxFetching import get_bounding_box_for_address, get_coordinates_for_address
from DatafordelerFetching import get_height_from_model, get_matrikel_from_address
import os
from dotenv import load_dotenv
import pyproj

load_dotenv()

DATAFORSYNING_TOKEN = os.getenv('DATAFORSYNING_TOKEN') 

def convert_coordinates(easting, northing, crs="EPSG:25832", from_crs="EPSG:4326"):
    """Converts coordinates from WGS84 (default) to a given CRS."""
    transformer = pyproj.Transformer.from_crs(from_crs, crs, always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    return (lon, lat)

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

def get_matrikel_geometry_on_image(address, item):
    """Returns the geometry of the matrikel."""
    matrikel_data = get_matrikel_from_address(address)
    coordinates = matrikel_data["features"][0]["geometry"]["coordinates"]
    crs = matrikel_data["features"][0]["geometry"]["crs"]["properties"]["name"]
    epsg_25832_coords = [convert_coordinates(coord[0], coord[1], "EPSG:25832", crs) for coord in coordinates[0]]

    epsg_25832_coords_with_height = [(coord[0], coord[1], get_height_from_model(coord[0], coord[1])) for coord in epsg_25832_coords]

    points_on_image = [calculate_point_on_image(item, coord[0], coord[1], coord[2]) for coord in epsg_25832_coords_with_height]

    return points_on_image

def fetch_images(address, token):
    """Fetches images from the Skraafoto API for a given address.
    Returns a list of tuples with the image data and the pixel coordinates of the address.
    """
    bbox = get_bounding_box_for_address(address)
    #coords = get_coordinates_for_address(address)

    collections = ["skraafotos2017", "skraafotos2019", "skraafotos2022"]
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

                    metadata = get_matrikel_geometry_on_image(address, response_json["features"][0])

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
    """Fetches and saves images for a given address."""
    image_tuples = fetch_images(address, token)
    i = 0
    metadata_str = "image_id,x,y\n"
    save_metadata(metadata_str, path)
    for image, metadata in image_tuples:
        my_image = Image.open(BytesIO(image)) 

        jpeg = convert_tiff_to_jpg(my_image)
        save_image(jpeg, path, str(i))
        
        metadata_str = "\n".join([str(i)+","+str(coord_pair[0])+","+str(coord_pair[1]) for coord_pair in metadata])+"\n"
        save_metadata(metadata_str, path)
        i += 1

# Example usage
get_and_save_images("Nyborgvej 69 Odense C", DATAFORSYNING_TOKEN, "output/nyborgvej69")
