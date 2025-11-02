# Launcher: run menu, then level_1 -> marketplace -> level_2 following exit codes.
import subprocess
import sys
import time

PY = sys.executable

def run_blocking(script):
    # Use relative script names only (expect to be launched from project root)
    try:
        res = subprocess.run([PY, script])
        return getattr(res, "returncode", 0)
    except Exception as e:
        print(f"[ERROR] running {script}: {e}")
        return None

def main():
    # 1) Run main_menu.py (blocking). If it exits with code 3 -> start full game flow.
    rc = run_blocking("main_menu.py")
    if rc is None:
        return
    if rc == 3:
        time.sleep(0.1)
        # 2) Run level_1 (relative path)
        rc1 = run_blocking("level_1.py")
        # After Level 1 completes, run marketplace
        rc_market = run_blocking("marketplace.py")
        # Convention: marketplace returns 2 to signal "start level_2"
        if rc_market == 2:
            run_blocking("level_2.py")
    else:
        print(f"[INFO] main_menu exited with code {rc}; launcher ending.")

if __name__ == "__main__":
    main()