from flask import Flask, request, jsonify, Response, redirect, send_file
import os
import json
from datetime import datetime
import time
from serial_commander import SerialCommander

app = Flask(__name__)

# Global data stores
config_data = {}
logs_data = []

# Initialize data from files if available
CONFIG_FILE = "config.json"
LOGS_FILE = "logs.json"
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
    except:
        config_data = {}
if os.path.exists(LOGS_FILE):
    try:
        with open(LOGS_FILE, 'r') as f:
            logs_data = json.load(f)
    except:
        logs_data = []

# Initialize serial commander 
commander = SerialCommander()
# commander.open()  


@app.route('/')
def serve_index():
    # If not configured yet, redirect to howto
    if not config_data:
        return redirect("/howto.html")
    return send_file("index.html")

@app.route('/howto.html')
def serve_howto():
    return send_file("howto.html")

@app.route('/logs.html')
def serve_logs():
    return send_file("logs.html")

@app.route('/style.css')
def serve_css():
    return send_file("style.css", mimetype='text/css')

@app.route('/api/saveConfig', methods=['POST'])
def save_config():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400
    # Save provided config (name and max weights)
    config_data.update(data)
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "ok"})

@app.route('/api/startSession')
def start_session():
    hand = request.args.get('hand', 'right')
    # Determine mode for new session
    mode = "strength"
    if logs_data:
        last_entry = logs_data[-1]
        today_str = datetime.now().strftime("%Y-%m-%d")
        if last_entry["date"] == today_str:
            # If an entry exists for today, use same mode (likely starting left-hand of the same day)
            mode = last_entry["mode"]
        else:
            # Alternate from last session's mode
            mode = "endurance" if last_entry["mode"] == "strength" else "strength"
    # Ensure config has needed key
    key = f"max_{mode}_{'R' if hand == 'right' else 'L'}"
    if key not in config_data:
        return jsonify({"status": "error", "message": "Configuration incomplete"}), 500
    weight = config_data[key]
    # Send commands to hardware
    commander.setSetPoint(weight*453.592)

    time.sleep(0.1)
    commander.setAutomaticMode()
    # Flush any lingering events in queue
    while True:
        ev = commander.get_event()
        if ev is None:
            break
    # Return session info
    return jsonify({ "mode": mode, "weight": weight, "name": config_data.get("name", "") })

@app.route('/api/submitResult', methods=['POST'])
def submit_result():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400
    needed = {"date", "mode", "right_weight", "right_reps", "left_weight", "left_reps"}
    if not needed.issubset(data.keys()):
        return jsonify({"status": "error", "message": "Missing fields"}), 400
    # Create log entry and append (replace any existing same date entry)
    log_entry = {
        "date": data["date"],
        "mode": data["mode"],
        "right_weight": data["right_weight"],
        "right_reps": data["right_reps"],
        "left_weight": data["left_weight"],
        "left_reps": data["left_reps"]
    }
    global logs_data
    logs_data = [entry for entry in logs_data if entry["date"] != log_entry["date"]]
    logs_data.append(log_entry)
    # Update adaptive training weights in config
    mode = data["mode"]
    if mode == "strength":
        for hand in ["R", "L"]:
            reps = data["right_reps"] if hand == "R" else data["left_reps"]
            key = f"max_strength_{hand}"
            current = config_data.get(key, data["right_weight"] if hand == "R" else data["left_weight"])
            if reps >= 10:
                new_max = current + 1
            else:
                drop = 10 - reps
                if drop > 3:
                    drop = 3
                new_max = current - drop
                if new_max < 1:
                    new_max = 1
            config_data[key] = new_max
    elif mode == "endurance":
        for hand in ["R", "L"]:
            reps = data["right_reps"] if hand == "R" else data["left_reps"]
            key = f"max_endurance_{hand}"
            current = config_data.get(key, data["right_weight"] if hand == "R" else data["left_weight"])
            if reps >= 20:
                new_max = current + 1
            else:
                drop = 20 - reps
                if drop > 3:
                    drop = 3
                new_max = current - drop
                if new_max < 1:
                    new_max = 1
            config_data[key] = new_max
    # Save logs and config to files
    try:
        with open(LOGS_FILE, 'w') as f:
            json.dump(logs_data, f)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "ok"})

@app.route('/api/logs')
def get_logs():
    return jsonify(logs_data)

@app.route('/api/delete', methods=['DELETE'])
def delete_log():
    date = request.args.get('date')
    if not date:
        return jsonify({"status": "error", "message": "Date not provided"}), 400
    global logs_data
    original_len = len(logs_data)
    logs_data = [entry for entry in logs_data if entry["date"] != date]
    if len(logs_data) == original_len:
        return jsonify({"status": "error", "message": "No entry found for that date"}), 404
    try:
        with open(LOGS_FILE, 'w') as f:
            json.dump(logs_data, f)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "ok"})

@app.route('/stream')
def stream():
    def event_stream():
        try:
            while True:
                event = commander.queue.get(block=True)
                print(event)
                yield f"data: {event}\n\n"
        except GeneratorExit:
            return
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
