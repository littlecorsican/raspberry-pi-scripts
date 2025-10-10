import os
import threading
import time
from flask import Flask, jsonify

app = Flask(__name__)


PORT = 8000
DELAY_BEFORE_OFF = 2

def _shutdown_worker():
    try:
        os.system("sync") # flush all buffered filesystem data to disk, best to do so so any unsaved docs are saved
        time.sleep(DELAY_BEFORE_OFF)
        os.system("sudo /sbin/shutdown -h now")
    except Exception as e:
        print(f"Shutdown error: {e}")

@app.route("/rpi/shutdown", methods=["GET"])
def shutdown():
    threading.Thread(target=_shutdown_worker, daemon=True).start()
    return jsonify({"status": "ok", "message": "Shutting down now."}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
