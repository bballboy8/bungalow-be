#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to print error messages
error() {
    echo "Error: $1" >&2
}

# Function to prompt user to install Python
prompt_install_python() {
    echo "Python is not installed on your system."
    echo "Please install Python from the official website: https://www.python.org/downloads/"
    exit 1
}

# Step 1: Check if Python is installed
echo "Checking if Python is installed..."
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
    echo "Python found: $(python3 --version)"
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
    echo "Python found: $(python --version)"
else
    prompt_install_python
fi

# Step 2: Check if the user can run Python scripts
echo "Verifying if Python scripts can be executed..."

# Detect if running on Windows
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Check if PowerShell execution policy is restricted (Windows specific)
    echo "Checking PowerShell execution policy..."

    PS_EXEC_POLICY=$(powershell -Command "Get-ExecutionPolicy")

    if [ "$PS_EXEC_POLICY" == "Restricted" ]; then
        echo "PowerShell execution policy is set to 'Restricted'."
        echo "Updating execution policy to 'RemoteSigned' to allow script execution."

        # Prompt user to change the execution policy (requires admin privileges)
        powershell -Command "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"

        # Recheck the execution policy to ensure it was set correctly
        NEW_PS_EXEC_POLICY=$(powershell -Command "Get-ExecutionPolicy")
        if [ "$NEW_PS_EXEC_POLICY" != "RemoteSigned" ]; then
            error "Failed to update the execution policy. Please run PowerShell as Administrator and execute:"
            echo "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
            exit 1
        else
            echo "Execution policy updated successfully to 'RemoteSigned'."
        fi
    else
        echo "PowerShell execution policy is already set to '$PS_EXEC_POLICY'."
    fi
else
    # Check Python script execution for non-Windows systems
    if $PYTHON_CMD -c "print('Python is working')" &>/dev/null; then
        echo "Python scripts are executable."
    else
        error "Cannot execute Python scripts. Please ensure you have the necessary permissions."
        echo "For Unix/Linux systems, you might need to adjust file permissions using chmod."
        echo "For Windows, ensure that Python is added to your PATH environment variable."
        exit 1
    fi
fi


# Step 3: Check if virtualenv is installed, and create a virtual environment if not present
VENV_DIR="venv"

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment '$VENV_DIR' already exists."
else
    echo "Virtual environment '$VENV_DIR' not found. Creating one..."
    
    # Check if virtualenv is installed
    if ! command -v virtualenv &>/dev/null; then
        echo "virtualenv is not installed. Installing virtualenv..."
        $PYTHON_CMD -m pip install --user virtualenv
        echo "virtualenv installed successfully."
    fi

    # Create the virtual environment
    virtualenv "$VENV_DIR"
    echo "Virtual environment '$VENV_DIR' created successfully."
fi

# Activate the virtual environment
echo "Activating the virtual environment..."
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Step 4: Install requirements from requirements.txt
REQUIREMENTS_FILE="requirements.txt"

if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing dependencies from '$REQUIREMENTS_FILE'..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
    echo "Dependencies installed successfully."
else
    error "'$REQUIREMENTS_FILE' not found."
    deactivate
    exit 1
fi

# Step 5: Run catelog_generator.py
PYTHON_SCRIPT="catelog_generator.py"

if [ -f "$PYTHON_SCRIPT" ]; then
    echo "Running '$PYTHON_SCRIPT'..."
    $PYTHON_CMD "$PYTHON_SCRIPT"
else
    error "'$PYTHON_SCRIPT' not found."
    deactivate
    exit 1
fi

# Deactivate the virtual environment
deactivate
echo "Virtual environment deactivated."
