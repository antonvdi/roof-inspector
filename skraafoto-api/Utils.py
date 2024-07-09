import pyproj

def convert_coordinates(easting, northing, crs="EPSG:25832", from_crs="EPSG:4326"):
    """Converts coordinates from WGS84 (default) to a given CRS."""
    transformer = pyproj.Transformer.from_crs(from_crs, crs, always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    return (lon, lat)