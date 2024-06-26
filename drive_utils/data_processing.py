import requests
import json
import geopandas as gpd
from shapely.geometry import Polygon
from drive_utils import drive_operations
from google.oauth2 import service_account
import os
import tempfile


def fetch_and_create_shapefile(api_url, district, parent_folder_id):
    """
    Fetches geographic data from a specified API, creates a shapefile, and saves it to Google Drive in a district-specific subfolder.
    
    Args:
    api_url (str): URL of the API endpoint to fetch data.
    district (str): District identifier used in naming the output shapefile and subfolder.
    parent_folder_id (str): Google Drive folder ID where the district subfolders are located.
    
    Returns:
    None
    """
    # Make a GET request to the API endpoint
    try:
        response = requests.get(api_url)
        response.raise_for_status()  
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return

    # Parse JSON response
    try:
        data = response.json()
    except json.JSONDecodeError:
        print("Failed to decode JSON from response")
        return

    if 'features' in data:
        features = data['features']
        properties_list = []
        geometry_list = []

        # Process each feature to extract geometry and attributes
        for feature in features:
            attributes = feature['attributes']
            properties_list.append(attributes)
            
            # Construct the geometry using shapely
            if 'geometry' in feature and 'rings' in feature['geometry']:
                polygon = Polygon([tuple(l) for l in feature['geometry']['rings'][0]])
                geometry_list.append(polygon)
            else:
                geometry_list.append(None)

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(properties_list, geometry=geometry_list)
        if not gdf.empty:
                print(gdf.head())

                creds = drive_operations.get_credentials()
                district_folder_id = drive_operations.create_or_find_subfolder(parent_folder_id, district)

                # temporarily save the shapefile locally in the /tmp directory
                with tempfile.TemporaryDirectory() as tmpdir:
                    shapefile_base_path = os.path.join(tmpdir, f"{district}.shp")
                    gdf.to_file(shapefile_base_path, driver='ESRI Shapefile')
                    
                    # Upload each generated file component to Google Drive
                    for file_name in os.listdir(tmpdir):
                        file_path = os.path.join(tmpdir, file_name)
                        if os.path.isfile(file_path):  
                            drive_operations.upload_file_to_drive(district_folder_id, file_path, file_name)

                print(f"Shapefiles for district {district} successfully uploaded to Google Drive.")
