from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from darknet_main import FishDetector
from pathlib import Path

app = Flask(__name__, static_folder='images')
IN_FOLDER = '/dnshare/server/images/in' # TODO your own path from the container
OUT_FOLDER = '/dnshare/server/images/out'
COUNT_FOLDER = '/dnshare/server/images/count'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['IN_FOLDER'] = IN_FOLDER
fishdetector = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_locked():
    return os.path.exists(IN_FOLDER)

def lock():
    open(IN_FOLDER, 'a').close()

def unlock():
    if is_locked():
        os.remove(IN_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def file_structure():
    global i
    i = 0

    if request.method == 'POST':
        files = request.files.getlist('files[]')
        upload_status = {'successful': [], 'rejected': []}
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(IN_FOLDER, filename)
                
                if not os.path.exists(file_path):
                    file.save(file_path)
                else:
                    upload_status['rejected'].append(filename)
                    print(f'Datei "{filename}" bereits vorhanden. Wird verworfen.')
        
        fishdetector.detect_fishes()
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(IN_FOLDER, filename)
                os.remove(file_path)
        
        upload_status['successful'].append(filename)

    # function to read in counts from .txt 
    def read_file_count():
        folder_count = []
       # iterate through all folders in the directory
        for folder_name in sorted(os.listdir(COUNT_FOLDER)):
            folder_full_path = os.path.join(COUNT_FOLDER, folder_name)
            # Check if directory
            if os.path.isdir(folder_full_path):
                # iterate through all files in the folder
                for file_name in sorted(os.listdir(folder_full_path)):
                    file_full_path = os.path.join(folder_full_path, file_name)
                    # check that only .txt are being read
                    if file_full_path.endswith('.txt'):
                        # open .txt and read count
                        with open(file_full_path, 'r') as file:
                            extracted_number = file.read().strip()
                            folder_count.append(extracted_number)
        return folder_count
    
    # function to read the directory structure 
    def read_folder_structure(folder, counts):
        global i
        folder_structure = []
        for item in sorted(os.listdir(folder)):
            item_path = os.path.join(folder, item)
            if os.path.isdir(item_path):
                # for folders: recursive function to read the structure of sub folders
                children = read_folder_structure(item_path, counts)
                folder_structure.append({'name': item, 'type': 'folder', 'children': children})
            else:
                # for files: attach count, if availabe
                count = counts[i] 
                folder_structure.append({'name': item, 'type': 'file', 'count': count})
                i = i + 1
        return folder_structure
 
    counts = read_file_count()
    folder_structure = read_folder_structure(OUT_FOLDER, counts)

    def get_newest_folder_path(folder):
        folders = [name for name in os.listdir(folder) if os.path.isdir(os.path.join(folder, name))]
        if not folders:
            return None
        newest_folder = max(folders, key=lambda x: os.path.getmtime(os.path.join(folder, x)))
        return os.path.join(folder, newest_folder)
    

    newest_folder_path = get_newest_folder_path(OUT_FOLDER)
    image_files = sorted(os.listdir(newest_folder_path))
    relative_newest_folder_path = newest_folder_path.replace('/dnshare/server/images/', '')

    def read_newest_folder_count():
        newest_folder_path_count = newest_folder_path.replace('/out/', '/count/')
        newest_folder_count = []
        
        for file_name in sorted(os.listdir(newest_folder_path_count)):
            file_full_path = os.path.join(newest_folder_path_count, file_name)
            if os.path.isfile(file_full_path) and file_name.endswith('.txt'):
                with open(file_full_path, 'r') as file:
                    extracted_number = file.read().strip()
                    newest_folder_count.append(extracted_number)
        return newest_folder_count

    newest_folder_path_count = read_newest_folder_count()

    return render_template('all.html', folder_structure=folder_structure, upload_message="", image_files=image_files, relative_newest_folder_path=relative_newest_folder_path, newest_folder_path_count=newest_folder_path_count)

if __name__ == '__main__':
    fishdetector = FishDetector()
    app.run(host='0.0.0.0', port=5000, debug=True)
