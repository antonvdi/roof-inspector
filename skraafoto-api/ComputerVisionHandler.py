import numpy as np
import cv2
import os
import csv
from shapely.geometry import Polygon
from PIL import Image, ImageDraw

def draw_polygon(image, coords, pixel_size, buffer=0.1):
    # Convert coordinates to a Shapely Polygon
    poly = Polygon(coords)
    
    pixel_buffer = buffer / pixel_size
    # Buffer the polygon to expand it by a certain distance
    buffered_poly = poly.buffer(distance=pixel_buffer, resolution=16, cap_style=3, join_style=2, mitre_limit=5.0)
    
    buffered_coords = list(buffered_poly.exterior.coords)
    
    # Create a mask with the same size as the image
    mask = Image.new('L', image.size, 0)
    ImageDraw.Draw(mask).polygon(buffered_coords, outline=1, fill=1)
    mask = np.array(mask)
    
    # Apply the mask to the image
    image_array = np.array(image)
    image_array = cv2.bitwise_and(image_array, image_array, mask=mask)
    
    # Crop the image to the bounding box of the buffered polygon
    minx, miny, maxx, maxy = buffered_poly.bounds
    cropped_image = image_array[int(miny):int(maxy), int(minx):int(maxx)]
    
    return Image.fromarray(cropped_image)

def load_data(base_id):
    image_points = {}
    csv_file = f"{base_id}.csv"  # CSV file with image points

    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            image_id = row['image_id']
            x = float(row['x'])
            y = float(row['y'])
            if image_id not in image_points:
                image_points[image_id] = {"points": []}
            image_points[image_id]["points"].append((x, y))
            image_points[image_id]["pixel_size"] = float(row['pixel_size'])

    for image_id, value in image_points.items():
        coords = np.array(value["points"], np.int32)
        image_path = os.path.join(f"{base_id}_{image_id}.jpg")
        image = Image.open(image_path)

        image_with_polygon = draw_polygon(image, coords, value["pixel_size"])
        
        image_with_polygon.show()

# Example usage
#load_data("output/valdemarsgade43")