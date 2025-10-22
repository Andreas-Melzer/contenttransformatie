import subprocess
import os
import sys
import mlflow
from config.settings import settings

def main():
    """
    Finds and runs the Streamlit applications
    """
    INTERNAL_PORT = 8501

    # --- Get Script Directory ---
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        print("Error: Cannot determine script directory. Are you running this interactively?")
        script_dir = os.path.abspath(os.getcwd())
        print(f"Warning: Assuming script directory is current working directory: {script_dir}")


    # --- Construct Path to Streamlit App ---
    app_file = os.path.join(script_dir, "interface", "0_Project_Selectie.py")

    if not os.path.exists(app_file):
        print(f"Error: Could not find the application file at {app_file}")
        print(f"Based on script location: {script_dir}")
        sys.exit(1)

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_file,
        "--server.port", str(INTERNAL_PORT),
        # Run headless so it doesn't try to open a browser on the server
        "--server.headless", "true",
    ]
    
    print(f"Project directory (cwd): {script_dir}")
    print(f"Executing command: {' '.join(command)}")
    # --- Detect Environment and Print URL ---
    
    print("\n" + "-"*53)
    ci_name = os.environ.get("CI_NAME")
    region = "No"
    if ci_name:
        print("Azure ML Environment Detected. Fetching workspace details...")
        try:
            from azure.ai.ml import MLClient
            from azure.identity import DefaultAzureCredential

            # These variables are reliably set on a compute instance
            subscription_id = settings.azure_subscription_id
            resource_group = settings.azure_resource_group
            workspace_name = settings.azure_workspace_name

            if not all([subscription_id, resource_group, workspace_name]):
                raise ValueError("Azure ML workspace environment variables not found.")

            ml_client = MLClient(
                DefaultAzureCredential(),
                subscription_id,
                resource_group,
                workspace_name
            )
            workspace = ml_client.workspaces.get(name=ml_client.workspace_name)
            # Get the region directly from the workspace properties
            region = workspace.location
            
            public_url = f"https://{ci_name}-{INTERNAL_PORT}.{region}.instances.azureml.ms"
            print(f"Your application should be accessible at:")
            print(public_url)

        except Exception as e:
            print(f"Could not automatically determine public URL: {e}")
            print("You may need to construct it manually.")

    else:
        print("Running locally.")
        print(f"Access your app at: http://localhost:{INTERNAL_PORT}")

    print("-"*53 + "\n")

    try:
        subprocess.run(command, check=True, cwd=script_dir)
    except FileNotFoundError:
        print("\nError: 'streamlit' command not found.")
        print("Please make sure Streamlit is installed in your Python environment.")
        print(f"(Environment: {sys.executable})")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running the Streamlit app: {e}")



if __name__ == "__main__":
    main()

