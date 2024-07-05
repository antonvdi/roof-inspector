import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
from BoundingBoxFetching import get_bounding_box_for_address, get_coordinates_for_address
import os
from dotenv import load_dotenv
import pyproj

load_dotenv()

DATAFORSYNING_TOKEN = os.getenv('DATAFORSYNING_TOKEN') 

def convert_from_wgs84(easting, northing, crs="EPSG:25832"):
    transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    lon, lat = transformer.transform(easting, northing)

    print(easting, northing, crs, lon, lat)
    return (lon, lat)

def get_metadata(item, coords):
    props = item["properties"]

    m11, m12, m13, m21, m22, m23, m31, m32, m33 = props["pers:rotation_matrix"]
    Xc, Yc, Zc = props["pers:perspective_center"]

    f_mm = props["pers:interior_orientation"]["focal_length"]
    ppo_x, ppo_y = props["pers:interior_orientation"]["principal_point_offset"]
    pixel_size = props["pers:interior_orientation"]["pixel_spacing"][0]
    sensor_cols, sensor_rows = props["pers:interior_orientation"]["sensor_array_dimensions"]
    

    # Calculated values. In pixels. Origo in image lower left.
    f = f_mm / pixel_size
    x0 = sensor_cols * 0.5 + ppo_x / pixel_size
    y0 = sensor_rows * 0.5 + ppo_y / pixel_size

    
    wgs84_coords = convert_to_wgs84(coords[0], coords[1], "EPSG:"+str(props["pers:crs"]))
    X, Y = wgs84_coords
    Z = 10

    dX = (X-Xc)
    dY = (Y-Yc)
    dZ = (Z-Zc)

    n = (m31 * dX + m32 * dY + m33 * dZ)

    xa = x0 - f * (m11 * dX + m12 * dY + m13 * dZ) / n
    ya = y0 - f * (m21 * dX + m22 * dY + m23 * dZ) / n

    ya_upper_left = sensor_rows - ya

    return (xa, ya_upper_left)

def fetch_images(address, token):
    bbox = get_bounding_box_for_address(address)
    coords = get_coordinates_for_address(address)

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

                    metadata = get_metadata(response_json["features"][0], coords)

                    image_response = requests.get(image_url, headers=headers)

                    if image_response.status_code == 200:
                        images.append((image_response.content, metadata))
                    else:
                        print(f"Failed to fetch the image data from {image_url}")
            else:
                print(f"Failed to fetch metadata from {url}")

    return images if images else None
    
def convert_tiff_to_jpg(image):
    jpeg_image = image.convert("RGB")
    return jpeg_image

def save_image(image, path, suffix=""):
    # if path is not set, make the path /output/image_<CURRENT TIME AND DATE>.jpg
    if path == None:
        path = "output/image_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + suffix + ".jpg"
    else:
        path = path + "_" + suffix + ".jpg"
    image.save(path)

def save_metadata(metadata, path, suffix=""):
    if metadata:
        with open(path + "_" + suffix + ".txt", "w") as file:
            file.write(metadata)

def get_and_save_images(address, token=DATAFORSYNING_TOKEN, path=None):
    image_tuples = fetch_images(address, token)
    i = 0
    for image, pixel_coords in image_tuples:
        my_image = Image.open(BytesIO(image)) 

        jpeg = convert_tiff_to_jpg(my_image)
        #save_image(jpeg, path, str(i))

        metadata = str(i)+","+str(pixel_coords[0])+","+str(pixel_coords[1])
        #save_metadata(metadata, path, str(i))
        i += 1

# Example usage
get_and_save_images("Nyborgvej 69 Odense C", DATAFORSYNING_TOKEN, "output/nyborgvej69")
