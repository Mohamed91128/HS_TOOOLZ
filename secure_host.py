from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import pandas as pd
from cryptography.fernet import Fernet
import zipfile
import io
import hashlib
import time
from functools import wraps

app = Flask(__name__)
CORS(app)

# Security configuration
SECRET_KEY = "your-super-secret-key-here"
ENCRYPTION_KEY = b'YourSecretKeyHere12345678901234567890123456789012='
cipher = Fernet(ENCRYPTION_KEY)

# File storage paths
GAMES_DIR = "secure_games"
DATABASE_FILE = "Game_Data_Updated.xlsx"

def require_api_key(f):
    """Decorator to require API key for access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != SECRET_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

def encrypt_file(file_data):
    """Encrypt file data"""
    return cipher.encrypt(file_data)

def decrypt_file(encrypted_data):
    """Decrypt file data"""
    return cipher.decrypt(encrypted_data)

@app.route('/api/games_database.xlsx', methods=['GET'])
@require_api_key
def get_games_database():
    """Serve encrypted games database"""
    try:
        if os.path.exists(DATABASE_FILE):
            with open(DATABASE_FILE, 'rb') as f:
                data = f.read()
            encrypted_data = encrypt_file(data)
            return encrypted_data, 200, {'Content-Type': 'application/octet-stream'}
        else:
            return jsonify({"error": "Database not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/games/<game_id>/<game_id>.<file_type>', methods=['GET'])
@require_api_key
def get_game_file(game_id, file_type):
    """Serve encrypted game files"""
    try:
        file_path = os.path.join(GAMES_DIR, game_id, f"{game_id}.{file_type}")
        
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        encrypted_data = encrypt_file(data)
        return encrypted_data, 200, {'Content-Type': 'application/octet-stream'}
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/upload_game', methods=['POST'])
@require_api_key
def upload_game():
    """Admin endpoint to upload new game files"""
    try:
        game_id = request.form.get('game_id')
        game_name = request.form.get('game_name')
        
        if not game_id or not game_name:
            return jsonify({"error": "Missing game_id or game_name"}), 400
        
        # Create game directory
        game_dir = os.path.join(GAMES_DIR, game_id)
        os.makedirs(game_dir, exist_ok=True)
        
        # Save uploaded files
        files = ['lua', 'json', 'folder', 'manifest']
        for file_type in files:
            if file_type in request.files:
                file = request.files[file_type]
                file_path = os.path.join(game_dir, f"{game_id}.{file_type}")
                file.save(file_path)
        
        # Update database
        update_database(game_id, game_name)
        
        return jsonify({"message": f"Game {game_id} uploaded successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def update_database(game_id, game_name):
    """Update the games database Excel file"""
    try:
        if os.path.exists(DATABASE_FILE):
            df = pd.read_excel(DATABASE_FILE)
        else:
            df = pd.DataFrame(columns=['GameID', 'GameName', 'UploadDate'])
        
        # Check if game already exists
        existing = df[df['GameID'] == game_id]
        if not existing.empty:
            df.loc[df['GameID'] == game_id, 'GameName'] = game_name
            df.loc[df['GameID'] == game_id, 'UploadDate'] = pd.Timestamp.now()
        else:
            new_row = pd.DataFrame({
                'GameID': [game_id],
                'GameName': [game_name],
                'UploadDate': [pd.Timestamp.now()]
            })
            df = pd.concat([df, new_row], ignore_index=True)
        
        df.to_excel(DATABASE_FILE, index=False)
        
    except Exception as e:
        print(f"Error updating database: {e}")

@app.route('/api/admin/list_games', methods=['GET'])
@require_api_key
def list_games():
    """Admin endpoint to list all games"""
    try:
        if os.path.exists(DATABASE_FILE):
            df = pd.read_excel(DATABASE_FILE)
            return jsonify(df.to_dict('records')), 200
        else:
            return jsonify([]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/delete_game/<game_id>', methods=['DELETE'])
@require_api_key
def delete_game(game_id):
    """Admin endpoint to delete a game"""
    try:
        # Remove from database
        if os.path.exists(DATABASE_FILE):
            df = pd.read_excel(DATABASE_FILE)
            df = df[df['GameID'] != game_id]
            df.to_excel(DATABASE_FILE, index=False)
        
        # Remove files
        game_dir = os.path.join(GAMES_DIR, game_id)
        if os.path.exists(game_dir):
            import shutil
            shutil.rmtree(game_dir)
        
        return jsonify({"message": f"Game {game_id} deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(GAMES_DIR, exist_ok=True)
    
    # Use existing database or create sample if not exists
    if not os.path.exists(DATABASE_FILE):
        print(f"Database file {DATABASE_FILE} not found. Please run excel_updater.py first.")
        sample_data = {
            'GameID': ['730', '570', '440'],
            'GameName': ['Counter-Strike 2', 'Dota 2', 'Team Fortress 2'],
            'UploadDate': [pd.Timestamp.now(), pd.Timestamp.now(), pd.Timestamp.now()]
        }
        df = pd.DataFrame(sample_data)
        df.to_excel(DATABASE_FILE, index=False)
    
    app.run(host='0.0.0.0', port=5000, ssl_context='adhoc') 