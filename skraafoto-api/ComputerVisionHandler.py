import csv
import os
from PIL import Image

import matplotlib.pyplot as plt
import matplotlib.patches as patches

def create_polygons_from_csv(base_id):
    csv_file = base_id + ".csv"
    image_points = {}
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            image_id = row['image_id']
            x = float(row['x'])
            y = float(row['y'])
            if image_id not in image_points:
                image_points[image_id] = {"points": []}  # Initialize with an empty list if not present
            image_points[image_id]["points"].append((x, y))

            
    # Read image from the image folder
    for image_id, value in image_points.items():
        coords = value["points"]
        image_path = os.path.join(f"{base_id}_{image_id}.jpg")
        image = Image.open(image_path)
    
        # Create polygon based on x and y points
        polygon = patches.Polygon(coords, closed=False)
        
        # Plot the image and polygon
        fig, ax = plt.subplots()
        ax.imshow(image)
        ax.add_patch(polygon)
        plt.show()

# Example usage
create_polygons_from_csv("output/nyborgvej69")