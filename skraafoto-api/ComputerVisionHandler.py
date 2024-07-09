import numpy as np
import cv2
from PIL import Image
import os
import csv
from shapely.geometry import Polygon

def draw_polygon(image, coords, pixel_size, buffer=1):
    # Convert coordinates to a Shapely Polygon
    poly = Polygon(coords)
    
    pixel_buffer = buffer / pixel_size
    # Buffer the polygon to expand it by a certain distance
    buffered_poly = poly.buffer(distance=pixel_buffer, resolution=16, cap_style=3, join_style=2, mitre_limit=5.0)
    
    if buffered_poly.is_empty:
        return image  # Return original image if buffering results in an empty polygon
    
    buffered_coords = list(buffered_poly.exterior.coords)
    
    # Convert buffered coordinates to a format suitable for cv2.polylines
    buffered_coords_int = np.array(buffered_coords, dtype=np.int32)
    
    image_array = np.array(image)
    
    # Draw the buffered polygon on the original image
    cv2.polylines(image_array, [buffered_coords_int], isClosed=True, color=(255, 0, 0), thickness=2)
    
    return Image.fromarray(image_array)

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
load_data("output/nyborgvej69")