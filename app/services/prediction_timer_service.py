"""
Prediction Timer Service

Manages prediction timer state for:
1. Result Selection Timer (1 minute after prediction closes)
"""

import time

import json
import os

# Timer state (Unix timestamps when timers end)
_result_selection_timer_end = 0  # 1-minute timer for result selection

def get_state_file_path():
    """Get path to the timer state file in user's BCU folder"""
    bcu_folder = os.path.join(os.path.expanduser("~"), "BCU")
    os.makedirs(bcu_folder, exist_ok=True)
    return os.path.join(bcu_folder, 'prediction_timer_state.json')

def save_timer_state():
    """Save current timer state to file"""
    data = {
        "result_selection_timer_end": _result_selection_timer_end
    }
    try:
        with open(get_state_file_path(), 'w') as f:
            json.dump(data, f)
        print(f"[PredictionTimer] State saved: {data}")
    except Exception as e:
        print(f"[PredictionTimer] Failed to save state: {e}")

def load_timer_state():
    """Load timer state from file"""
    global _result_selection_timer_end
    try:
        path = get_state_file_path()
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                _result_selection_timer_end = data.get("result_selection_timer_end", 0)
            print(f"[PredictionTimer] State loaded: {data}")
    except Exception as e:
        print(f"[PredictionTimer] Failed to load state: {e}")

def start_result_selection_timer():
    """Start 1-minute timer when prediction closes (마감).
    Only starts if timer is not already running to prevent reset."""
    global _result_selection_timer_end
    
    # Check if timer is already running (has remaining time)
    if _result_selection_timer_end > time.time():
        remaining = _result_selection_timer_end - time.time()
        print(f"[PredictionTimer] Result selection timer already running. {int(remaining)} seconds remaining. Skipping reset.")
        return
    
    _result_selection_timer_end = time.time() + 60  # 60 seconds
    save_timer_state()
    print(f"[PredictionTimer] Result selection timer started. Ends at: {_result_selection_timer_end}")


def get_result_selection_remaining():
    """Get remaining seconds for result selection timer"""
    remaining = _result_selection_timer_end - time.time()
    return max(0, int(remaining))


def get_timer_status():
    """Get status of timers"""
    return {
        "result_selection_remaining": get_result_selection_remaining()
    }

# Initialize state on module load
load_timer_state()
