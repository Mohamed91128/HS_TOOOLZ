from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import uuid
import json
import os

app = Flask(__name__)
KEYS_FILE = "keys.json"

# Load all stored keys
def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, 'r') as f:
        return json.load(f)

# Save keys to file
def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f)

# Endpoint: /genkey
@app.route("/genkey")
def generate_key():
    keys = load_keys()

    # Generate a truly unique key that doesn't exist yet
    while True:
        new_key = str(uuid.uuid4())
        if new_key not in keys:
            break

    expiration = (datetime.now() + timedelta(hours=24)).isoformat()
    keys[new_key] = {
        "expires": expiration,
        "used": False
    }

    save_keys(keys)
    return jsonify({"key": new_key, "expires": expiration})

# Endpoint: /verify?key=XXXX
@app.route("/verify")
def verify_key():
    key = request.args.get("key")
    if not key:
        return jsonify({"valid": False, "reason": "No key provided"}), 400

    keys = load_keys()
    key_data = keys.get(key)

    if not key_data:
        return jsonify({"valid": False, "reason": "Key not found"}), 404

    # Already used?
    if key_data.get("used", False):
        return jsonify({"valid": False, "reason": "Key already used"}), 403

    # Expired?
    if datetime.fromisoformat(key_data["expires"]) < datetime.now():
        return jsonify({"valid": False, "reason": "Expired"}), 403

    # Mark as used
    keys[key]["used"] = True
    save_keys(keys)

    return jsonify({"valid": True, "message": "Key is valid and now marked as used."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
