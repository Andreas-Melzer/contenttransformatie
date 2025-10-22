#!/bin/bash

# --- Configuration ---
CONDA_ENV_NAME="content"
PYTHON_SCRIPT_NAME="run_interface.py"
# ---------------------

echo "Attempting to start the application..."

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Changing directory to: $SCRIPT_DIR"
cd "$SCRIPT_DIR"

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "Error: 'conda' command not found."
    echo "Please make sure Conda (Miniconda/Anaconda) is installed and configured in your shell."
    exit 1
fi

# Activate Conda environment using the recommended 'hook'
# This initializes conda for the current shell session
echo "Initializing Conda..."
eval "$(conda shell.bash hook)"

# Check if the Conda environment exists
if ! conda env list | grep -q "^$CONDA_ENV_NAME\s"; then
    echo "Environment '$CONDA_ENV_NAME' not found."
    
    # Check if environment.yml exists before trying to create from it
    if [ -f "environment.yml" ]; then
        echo "Creating environment from environment.yml. This may take a few minutes..."
        conda env create -q --file environment.yml
        if [ $? -ne 0 ]; then
            echo "Error: Failed to create Conda environment from environment.yml."
            exit 1
        fi
        echo "Environment created successfully."
    else
        echo "Error: environment.yml not found. Cannot create the required environment."
        exit 1
    fi
else
    echo "Environment '$CONDA_ENV_NAME' already exists."
fi


echo "Activating Conda environment: $CONDA_ENV_NAME"
conda activate "$CONDA_ENV_NAME"

# Check if activation was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate Conda environment '$CONDA_ENV_NAME'."
    echo "Please ensure the environment is set up correctly."
    exit 1
fi

echo "Running Python script: $PYTHON_SCRIPT_NAME"
# Execute the python script
# This script will now run within the activated environment
# and with the correct working directory.
python "$PYTHON_SCRIPT_NAME"

echo "Application script finished."
