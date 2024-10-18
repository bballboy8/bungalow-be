import os
import csv

def check_csv_and_rename_output_dir(OUTPUT_CSV_FILE, OUTPUT_DIR, START_DATE, END_DATE, output_base_dir, vendor_name):
    with open(OUTPUT_CSV_FILE, 'r') as f:
        reader = csv.reader(f)
        row_count = sum(1 for _ in reader)
        
        if row_count < 2:
            print("No data found for the given parameters")
            new_output_dir = os.path.join(output_base_dir, f"{vendor_name}/0_{START_DATE}_{END_DATE}")
            
            if os.path.exists(new_output_dir):
                counter = 1
                while os.path.exists(f"{new_output_dir}_{counter}"):
                    counter += 1
                new_output_dir = f"{new_output_dir}_{counter}"
            
            os.rename(OUTPUT_DIR, new_output_dir)


def check_folder_content_and_rename_output_dir(OUTPUT_THUMBNAIL_FOLDER, OUTPUT_DIR, START_DATE, END_DATE, output_base_dir, vendor_name):
    if len(os.listdir(OUTPUT_THUMBNAIL_FOLDER)) == 0:
        print("No data found for the given parameters")
        new_output_dir = os.path.join(output_base_dir, f"{vendor_name}/0_{START_DATE}_{END_DATE}")
        
        if os.path.exists(new_output_dir):
            counter = 1
            while os.path.exists(f"{new_output_dir}_{counter}"):
                counter += 1
            new_output_dir = f"{new_output_dir}_{counter}"
        
        os.rename(OUTPUT_DIR, new_output_dir)