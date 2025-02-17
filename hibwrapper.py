import subprocess
import os
import sys
import time
import ctypes

def bring_window_to_front():
    """Brings the terminal window to the foreground to alert the user."""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # Restore window if minimized
            ctypes.windll.user32.SetForegroundWindow(hwnd)  # Bring to front
    except Exception as e:
        print(f"Failed to bring window to front: {e}")

def run_script_and_hibernate(script_path):
    try:
        # Run the designated script and wait for it to finish
        result = subprocess.run(["python", script_path], check=True)
        print(f"{script_path} exited with code {result.returncode}")

        # Notify user and wait for 10 minutes before hibernation
        print("\nSystem will hibernate in 10 minutes. Press Ctrl+C to cancel.")
        bring_window_to_front()
        time.sleep(600)  # Wait 10 minutes

        # Hibernate the system
        print("Hibernating...")
        os.system("shutdown /h")

    except subprocess.CalledProcessError as e:
        print(f"Script failed with return code {e.returncode}")
    except KeyboardInterrupt:
        print("\nHibernate canceled by user.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hibwrapper.py <script_to_run.py>")
        sys.exit(1)

    script_to_run = sys.argv[1]
    run_script_and_hibernate(script_to_run)
