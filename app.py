import os
import hashlib
import json
from flask import Flask, request, jsonify, render_template
import logging
from werkzeug.utils import secure_filename
import redis,sys

# globals
r=None

REDIS_HOST = os.getenv('REDIS_HOST', ',my_redis_2')  
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


###################################################################################
# Check Redis server existence
def check_redis_connection():
    global r
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping() 
        logging.info(f"Connected to Redis({REDIS_HOST}:{REDIS_PORT}) successfully.")
    except redis.ConnectionError as e:
        logging.error(f"**** Connection to Redis ({REDIS_HOST}:{REDIS_PORT}) failed: {e} ****")
        logging.error(f"*** Exiting the application ***")
        sys.exit(1)  


###################################################################################
# Check filename extesions
#
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


###################################################################################
# Calculate has has over the file, using 8192 chunk size for calculations
#
def calculate_file_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

###################################################################################
# Store image hash and given name to Redis (hash being the key)
# 
def store_image_info(redis_client, file_path, file_name, name):
    
    try:
        file_hash = calculate_file_hash(file_path)
        key = f"image:{file_hash}"
        
        old_name = redis_client.get(key)
        if old_name:
            #old_name = old_name.decode("utf-8")
            logging.info(f"Old name: {old_name}")
            if old_name != name:
                logging.info(f"File {key} exists. Updating name {old_name} -> {name}")
                redis_client.set(key, name)
                return True
            else:
                logging.info(f"File {key} exists with same name:{name}")
                return True
        else:
            logging.info(f"New file. Adding info {key} --> {name}")
            redis_client.set(key, name)
            return True
    except Exception as e:
        logging.error(f"Error storing image info for {name}")
        return False
    


    

#####################################################################################
#STARTUP CODE


# redis is-it-alive check
check_redis_connection()

###################################################################################
# REST API SECTION
###################################################################################

###################################################################################
# InitiL web page. Form to send file
#
@app.route('/')
def index():
    return render_template('upload_form.html')

###################################################################################
# Upload image and name
# 
# curl -X POST -F "name=Mika" -F "file=@kuva.png" http://localhost:5000/upload
#
@app.route('/upload', methods=['POST'])
def upload_file():
    logging.info(f"** UPLOAD SECTION ****")

    UPLOADFLAG=None
    REDISUPDATEFLAG=None

    name = request.form.get('name')
    file = request.files.get('file')

    if not name or not file:
        return jsonify({'error': 'Name and file required'}), 400
    
    if not allowed_file(file.filename):
        logging.error(f"ERROR: Not allowed filetype: {file}")
        return jsonify({'error': 'Invalid file type'}), 400

    logging.info(f"Received data, name:{name} ,file:{file}")


    filename = secure_filename(file.filename) #filtering
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    try:
        file.save(filepath)
        logging.info(f"File saved to {filepath}")
        UPLOADFLAG=True
    except Exception as e:
        logging.error(f"Failed to save file({filepath}): {e}")
        UPLOADFLAG=False
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500


    file_hash = calculate_file_hash(filepath)
    logging.info(f"File:{file}, file_hash:{file_hash}")

 
    # hash of pic --> file name to Redis
    REDISUPDATEFLAG=store_image_info(r, filepath, filename, name)
    if (REDISUPDATEFLAG and UPLOADFLAG):
        logging.info(f"Upload OK. file:{file} name:{filepath}")
        return jsonify({'message': 'Upload successful', 'file_hash': file_hash})
    else:
        logging.error(f"Upload ERROR: file:{file} name:{filepath}")
        return jsonify({'error': f'Failed to save file: {filepath}'}), 500

##########################################################################
# Get hash (image name) added name
#
# curl -X GET http://localhost:5000/lookup/234dd59656f803ce7b553579dcf0054ac236032a838f462ef5425d8dc023db4f
#
@app.route('/lookup/<file_hash>', methods=['GET'])
def lookup(file_hash):
    logging.info(f"*** Checking hash {file_hash}*** ")
    
    key = f"image:{file_hash}"
    try:
        name = r.get(key)
        if name:
            logging.info("OK: Hash:{file_hash} ---> {name}")
            return jsonify({'name': name})
        else:
            logging.error(f"ERROR: Hash:{file_hash} not found")
            return jsonify({'error': 'Hash not found'}), 404
    except Exception as e:
        logging.error(f"Error while fetching hash {file_hash} from Redis: {e}")
        return jsonify({'error': 'Internal Redis server error'}), 500

######################################################################################################
# Get all Redis data (to log and JSON return)
#
# curl -X GET http://localhost:5000/l/api/get_all_keys
@app.route('/api/get_all_keys', methods=['GET'])
def get_all_keys():
    try:
        keys = r.keys('*')  # all keys
        data = {}

        for key in keys:
            value = r.get(key)
            if value:
                # key-> value to dictionary
                data[key] = value

        logging.info(f"ALL REDIS DATA:{data}")
        return jsonify(data), 200  

    except Exception as e:
        logging.error("ERROR. Could not get all Redis data")
        return jsonify({'error': str(e)}), 500  
    
######################################################################################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
