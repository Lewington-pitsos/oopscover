import os
import shutil

def filter_files_by_content(dir_path, target_string, new_dir):
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        if not os.path.isfile(file_path):
            continue
        
        with open(file_path, 'r', errors='ignore') as f:
            if target_string.lower() in f.read().lower():
                shutil.copy(file_path, os.path.join(new_dir, filename))


filter_files_by_content('data/www.health.gov.au', 'medicare', 'data/medicare')