'''

url:  https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/Data-API/planet_python_client_introduction.ipynb

'''

# Set your API key here
import requests
import json
import csv
import io
import pygeohash as pgh
from datetime import datetime, timedelta
from dateutil import parser
import argparse
import os
from tqdm import tqdm

import shutil

# Get the terminal size
columns = shutil.get_terminal_size().columns

# Input configuration
API_KEY = 'PLAKba216105b17b4dbda5e1cdfec67ba836'
# START_DATE = '2024-01-01'  # Specify the start date in 'YYYY-MM-DD' format
# END_DATE = '2024-08-07'    # Specify the end date in 'YYYY-MM-DD' format
GEOHASH = 'w'              # Specify the initial geohash
GEOHASH_LENGTH = 2         # Specify the desired geohash length
ITEM_TYPE = "SkySatCollect"  # Specify the item type

# Output files
# OUTPUT_CSV_FILE = r'O:\Professional__Work\Heimdall\planet\output_planet.csv'
# OUTPUT_GEOJSON_FILE = r'O:\Professional__Work\Heimdall\planet\output_planet.geojson'


# Function to get the corners of the geohash
def get_geohash_corners(geohash):
    center_lat, center_lon = pgh.decode(geohash)
    lat_err, lon_err = pgh.decode_exactly(geohash)[-2:]
    top_left = (center_lat + lat_err, center_lon - lon_err)
    top_right = (center_lat + lat_err, center_lon + lon_err)
    bottom_left = (center_lat - lat_err, center_lon - lon_err)
    bottom_right = (center_lat - lat_err, center_lon + lon_err)
    return {
        "top_left": top_left,
        "top_right": top_right,
        "bottom_left": bottom_left,
        "bottom_right": bottom_right
    }


# Function to convert geohash to GeoJSON
def geohash_to_geojson(geohash_str: str) -> dict:
    corners = get_geohash_corners(geohash_str)
    return {
        "type": "Polygon",
        "coordinates": [[
            [corners["top_left"][1], corners["top_left"][0]],  # NW corner
            [corners["top_right"][1], corners["top_right"][0]],  # NE corner
            [corners["bottom_right"][1], corners["bottom_right"][0]],  # SE corner
            [corners["bottom_left"][1], corners["bottom_left"][0]],  # SW corner
            [corners["top_left"][1], corners["top_left"][0]]  # NW corner again to close the polygon
        ]]
    }

def latlon_to_geohash(lat, lon, range_km):
    # Map the range to geohash precision
    precision = (
        2 if range_km > 100 else
        4 if range_km > 20 else
        6 if range_km > 5 else
        8 if range_km > 1 else
        10
    )
    return pgh.encode(lat, lon, precision=precision)


# Function to generate an array of geohashes from a seed geohash
def generate_geohashes(seed_geohash, child_length):
    base32_chars = '0123456789bcdefghjkmnpqrstuvwxyz'

    def generate_geohashes_recursive(current_geohash, target_length, result):
        if len(current_geohash) == target_length:
            result.append(current_geohash)
            return
        for char in base32_chars:
            next_geohash = current_geohash + char
            generate_geohashes_recursive(next_geohash, target_length, result)

    result = []
    generate_geohashes_recursive(seed_geohash, len(seed_geohash) + child_length, result)
    return result


# Function to calculate the withhold time
def calculate_withhold_time(acquisition_date, publication_date):
    """Calculate the withhold time as total hours and formatted string."""
    acq_date = parser.isoparse(acquisition_date)
    pub_date = parser.isoparse(publication_date)
    delta = pub_date - acq_date
    total_hours = int(delta.total_seconds() / 3600)
    days, remaining_hours = divmod(total_hours, 24)
    readable = f"{days} days {remaining_hours} hours"
    return readable, total_hours


# Function to format datetime
def format_datetime(datetime_str):
    """Format datetime string to 'YYYY-MM-DD HH:MM:SS.xx'."""
    try:
        dt = parser.isoparse(datetime_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]  # Truncate to two decimal places
    except (ValueError, TypeError):
        return datetime_str


# Function to format float
def format_float(value, precision=2):
    """Format float to a string with the given precision."""
    try:
        return f"{float(value):.{precision}f}"
    except ValueError:
        return "0.00"  # Default if there's an error


# Function to query Planet data
def query_planet_data(aoi_geojson, start_date, end_date, item_type):
    search_endpoint = "https://api.planet.com/data/v1/quick-search"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'api-key ' + API_KEY
    }
    request_payload = {
        "item_types": [item_type],
        "filter": {
            "type": "AndFilter",
            "config": [
                {
                    "type": "GeometryFilter",
                    "field_name": "geometry",
                    "config": aoi_geojson
                },
                {
                    "type": "DateRangeFilter",
                    "field_name": "acquired",
                    "config": {
                        "gte": start_date,
                        "lte": end_date
                    }
                }
            ]
        }
    }

    try:
        response = requests.post(search_endpoint, headers=headers, json=request_payload)
        response.raise_for_status()
        features = response.json()['features']
        return features
    except requests.RequestException as e:
        # print(f"Failed to fetch data: {str(e)}")
        return []


# Function to save features to CSV and GeoJSON
def save_features_to_files(features, output_dir='.'):
    # Prepare CSV output
    OUTPUT_CSV_FILE = f"{output_dir}/output_planet.csv"
    os.makedirs(output_dir, exist_ok=True)  # Creates the directory if it doesn't exist

    OUTPUT_GEOJSON_FILE = f"{output_dir}/output_planet.geojson"
    os.makedirs(output_dir, exist_ok=True)  # Creates the directory if it doesn't exist

    with open(OUTPUT_CSV_FILE, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

        # Write the header row
        csv_writer.writerow([
            'id', 'geometry', 'acquired', 'cloud_percent',
            'item_type', 'provider', 'published',
            'satellite_azimuth', 'satellite_id', 'view_angle',
            'pixel_resolution', 'withhold_readable', 'withhold_hours'
        ])

        # Prepare GeoJSON output
        geojson_features = []

        # Write the data rows
        for feature in features:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            acquisition_date = format_datetime(properties.get('acquired', ''))
            publication_date = format_datetime(properties.get('published', ''))
            withhold_readable, withhold_hours = calculate_withhold_time(properties.get('acquired', ''),
                                                                        properties.get('published', ''))
            satellite_azimuth = format_float(properties.get('satellite_azimuth', ''), 2)
            view_angle = format_float(properties.get('view_angle', ''), 2)
            pixel_resolution = format_float(properties.get('pixel_resolution', ''), 2)

            csv_writer.writerow([
                feature.get('id', ''),
                json.dumps(geometry),  # Geometry as a JSON string
                acquisition_date,
                properties.get('cloud_percent', ''),
                properties.get('item_type', ''),
                properties.get('provider', ''),
                publication_date,
                satellite_azimuth,
                properties.get('satellite_id', ''),
                view_angle,
                pixel_resolution,
                withhold_readable,
                withhold_hours
            ])

            # Create a GeoJSON feature
            geojson_feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "id": feature.get('id', ''),
                    "acquired": acquisition_date,
                    "cloud_percent": properties.get('cloud_percent', ''),
                    "item_type": properties.get('item_type', ''),
                    "provider": properties.get('provider', ''),
                    "published": publication_date,
                    "satellite_azimuth": satellite_azimuth,
                    "satellite_id": properties.get('satellite_id', ''),
                    "view_angle": view_angle,
                    "pixel_resolution": pixel_resolution,
                    "withhold_readable": withhold_readable,
                    "withhold_hours": withhold_hours
                }
            }
            geojson_features.append(geojson_feature)

    # Save the GeoJSON file
    geojson_output = {
        "type": "FeatureCollection",
        "features": geojson_features
    }

    with open(OUTPUT_GEOJSON_FILE, 'w') as geojson_file:
        json.dump(geojson_output, geojson_file, indent=4)

    # print(f"CSV and GeoJSON files have been saved:\nCSV: {OUTPUT_CSV_FILE}\nGeoJSON: {OUTPUT_GEOJSON_FILE}")


# Main function to process all dates first and then save the files
def main(START_DATE, END_DATE, OUTPUT_DIR, GEOHASH):
    # seed_geohash = GEOHASH
    # child_length = int(GEOHASH_LENGTH) - 1
    # geohashes = generate_geohashes(seed_geohash, child_length)

    geohashes = [GEOHASH]

    current_date = datetime.strptime(START_DATE, '%Y-%m-%d')
    end_date = datetime.strptime(END_DATE, '%Y-%m-%d')

    duration = (end_date - current_date).days + 1
    all_features = []  # Collect all features for all dates
    print("-"*columns)
    description = f"Processing Planet Catalog \nDate Range: {current_date.date()} to {end_date.date()} \n lat: {LAT} and lon: {LON} Range:{RANGE} \nOutput Directory: {OUTPUT_DIR}"
    print(description)
    print("-"*columns)
    print("Duration :", duration, "days" if duration > 1 else "day")
    # Iterate over each day in the date range
    with tqdm(total=duration, desc="", unit="date") as pbar:

        while current_date <= end_date:
            start_time = current_date.strftime('%Y-%m-%dT00:00:00Z')
            end_time = current_date.strftime('%Y-%m-%dT23:59:59Z')
            date_str = current_date.strftime('%Y-%m-%d')

            # Process each geohash
            for geohash in geohashes:
                # print(f"Processing date: {date_str}, Geohash: {geohash}")
                AOI_GEOJSON = geohash_to_geojson(geohash)
                features = query_planet_data(AOI_GEOJSON, start_time, end_time, ITEM_TYPE)
                all_features.extend(features)

            current_date += timedelta(days=1)

            pbar.refresh()
            pbar.update(1)

        pbar.clear()
    tqdm.write("Completed processing Planet data")

    # Save all collected features to files after processing all days
    save_features_to_files(all_features, OUTPUT_DIR)


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(description='Plant Catelog API Executor')
    argument_parser.add_argument('--start-date', required=True, help='Start date')
    argument_parser.add_argument('--end-date', required=True, help='End date')
    argument_parser.add_argument('--lat', required=True, type=float, help='Latitude')
    argument_parser.add_argument('--long', required=True, type=float, help='Longitude')
    argument_parser.add_argument('--range', required=True, type=float, help='Range value')
    argument_parser.add_argument('--output-dir', required=True, help='Output directory')

    args = argument_parser.parse_args()
    START_DATE = args.start_date
    END_DATE = args.end_date
    OUTPUT_DIR = args.output_dir + f"/planet/{START_DATE}_{END_DATE}"

    RANGE = int(args.range)
    LAT, LON = args.lat, args.long
    GEOHASH = latlon_to_geohash(LAT, LON, range_km=RANGE)
    print(f"Generated Geohash: {GEOHASH}")

    # Check if the directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    main(
        START_DATE,
        END_DATE,
        OUTPUT_DIR,
        GEOHASH
    )