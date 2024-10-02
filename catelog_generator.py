import subprocess
import concurrent.futures
import sys
import os

# Define the paths to the scripts
scripts = [
    "airbus_catalog_api.py",
    "capella_master_collector.py",
    "planet_catalog_api.py",
    "skyfi_catalog_api.py"
]

# Parameters to be passed to each script
params = {
    'start_date': '2020-08-29',
    'end_date': '2020-09-01',
    'lat': 40.7128,
    'long': -74.0060,
    'range': 100.0,
    'output_dir': '/Users/amankhan/Desktop/catalogs'
}

def check_directory_permissions(output_dir):
    # Check if the directory exists
    if not os.path.exists(output_dir):
        try:
            # Attempt to create the directory
            os.makedirs(output_dir)
            print(f"Directory {output_dir} created successfully.")
        except Exception as e:
            print(f"Error creating directory {output_dir}: {e}")
            return False

    # Check if the directory is writable
    if os.access(output_dir, os.W_OK):
        return True
    else:
        print(f"Write permission denied for directory {output_dir}")
        return False

def run_script(script_name):
    if not check_directory_permissions(params['output_dir']):
        print(f"Skipping {script_name} due to directory issues.")
        return
    
    cmd = [
        "python", script_name,
        "--start-date", params['start_date'],
        "--end-date", params['end_date'],
        "--lat", str(params['lat']),
        "--long", str(params['long']),
        "--range", str(params['range']),
        "--output-dir", params['output_dir']
    ]
    
    print(f"Running {script_name}...")
    result = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
    
    if result.returncode == 0:
        print(f"{script_name} completed successfully.")
    else:
        print(f"Error in {script_name}: {result.stderr}")

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_script, script) for script in scripts]
        
        concurrent.futures.wait(futures)
