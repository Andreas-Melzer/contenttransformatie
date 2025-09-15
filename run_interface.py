import subprocess
import os
import sys

def main():
    """
    Finds and runs the Streamlit application using a relative path.
    This script is intended to be run from the root of the project directory.
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(__file__)

    # Construct the path to the Streamlit entrypoint file
    # os.path.join ensures the path is correct for any OS (e.g., uses \ on Windows, / on Linux/Mac)
    app_file = os.path.join(script_dir, "interface", "0_Project_Selectie.py")

    # Check if the file actually exists before trying to run it
    if not os.path.exists(app_file):
        print(f"Error: Could not find the application file at {app_file}")
        print("Please ensure this script is in the root directory of your project.")
        sys.exit(1)

    # The command to execute
    # Using sys.executable ensures we use the same python interpreter that is running this script
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_file
    ]

    print(f"Starting Streamlit app...")
    print(f"Executing command: {' '.join(command)}")

    # Run the command
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        print("\nError: 'streamlit' command not found.")
        print("Please make sure Streamlit is installed in your Python environment.")
        print("Try running: pip install streamlit")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running the Streamlit app: {e}")

if __name__ == "__main__":
    main()
