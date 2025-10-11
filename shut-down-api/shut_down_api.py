import os
import threading
import time
from flask import Flask, jsonify, request
from functools import wraps
import settings

app = Flask(__name__)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #skip auth if disabled
        if not settings.ENABLE_API_AUTH:
            return f(*args, **kwargs)
        
        #check api key in headers or query param
        api_key = request.headers.get('X-Api-Key') or request.args.get('api_key')
        
        if api_key and api_key == settings.API_KEY:
            return f(*args, **kwargs)
        
        else:
            return jsonify({"status": "error", "message": "Unauthorized. Invalid or missing API key"}), 401
            
    return decorated_function

def _shutdown_worker(): #standalone helper function to handle shutdown
    try:
        os.system("sync") # flush all buffered filesystem data to disk, best to do so so any unsaved docs are saved
        time.sleep(settings.DELAY_BEFORE_OFF)
        os.system("sudo /sbin/shutdown -h now")

    except Exception as e:
        print(f"Shutdown error: {e}")

@app.route("/rpi/shutdown", methods=["GET"])
@require_api_key
def shutdown():
    threading.Thread(target=_shutdown_worker, daemon=True).start()
    return jsonify({"status": "ok", "message": "Shutting down now."}), 200

if __name__ == "__main__":
    print(f"Starting shutdown API server on port {settings.PORT}")
    if settings.ENABLE_API_AUTH:
        print("API authentication is enabled")
        if not settings.API_KEY:
            print("WARNING: No API key configured in .env file!")

    else:
        print("API authentication is disabled")

    app.run(host="0.0.0.0", port=settings.PORT)
