# bungalow-be


# Python Environment Setup and Script Execution

This guide will walk you through setting up your Python environment and running the provided Bash script in **PyCharm**.

## Prerequisites

Before running the script, ensure the following:

1. **Python Installed**:
   - Make sure Python is installed on your machine.
   - If not, download and install it from [python.org](https://www.python.org/downloads/).

2. **PyCharm Installed**:
   - Download and install **PyCharm** from [JetBrains](https://www.jetbrains.com/pycharm/download/).
   - PyCharm provides a built-in terminal that allows you to run bash scripts.

## Steps to Run the Setup Script in PyCharm

### 1. Clone or Download the Project

- Clone the project from your repository or download the zip file containing the project.
- Extract it and open the project folder in PyCharm.

### 2. Locate the Setup Script

The setup script is named `setup_and_run.sh`. You can find it in the root directory of the project.

### 3. Open the Terminal in PyCharm

To run the script:

1. Go to the **bottom panel** of PyCharm and click on the **Terminal** tab. If the terminal is not visible, you can enable it from the **View > Tool Windows > Terminal** menu.
2. Or you can use shortcut `Alt + F12` to open the terminal.

### 4. Make the Script Executable (for Unix-based Systems)

Before running the script, ensure it has the right execution permissions. In the terminal, run:

```bash
chmod +x setup_and_run.sh
```

This command will give the script executable permissions.

### 5. Run the Script

To run the script, enter the following command in the PyCharm terminal:

```bash
./setup_and_run.sh
```

### 6. Follow the Prompts

The script will perform the following steps:

1. **Check for Python installation**:
   - If Python is not installed, you will be prompted to install it.
   
2. **Check if Python scripts are executable**:
   - On **Windows**, the script will adjust the PowerShell execution policy if it's restricted.
   - On **Unix/Linux/macOS**, the script will check if Python scripts can be executed.
   
3. **Create or use a virtual environment**:
   - If a virtual environment (`venv`) doesn't already exist, the script will create one using `virtualenv`.
   
4. **Install dependencies**:
   - The script will install all dependencies listed in the `requirements.txt` file.

5. **Run the Python script**:
   - After setting up the environment, the script will run `catelog_generator.py`.

### 7. View the Output

After the script completes, you will see the output of the `catelog_generator.py` Python script in the terminal.

### 8. Customizing Parameters in catelog_generator.py

The script catelog_generator.py uses a dictionary called params to configure various settings for generating catalogs, such as the date range, location, and output directory. You can easily modify these parameters to suit your needs.

Default Parameters
The default values for the parameters are as follows:

``` python

params = {
    'start_date': '2020-08-29',
    'end_date': '2020-09-01',
    'lat': 40.7128,  # Latitude (New York City in this example)
    'long': -74.0060,  # Longitude (New York City in this example)
    'range': 100.0,  # Range in kilometers
    'output_dir': '/Users/username/Desktop/catalogs' if platform.system() != "Windows" else 'C:\\Users\\username\\Desktop\\catalogs'
}
```

Parameters Explained:
- start_date: The start date for generating catalogs, in the format YYYY-MM-DD.
- end_date: The end date for generating catalogs, in the format YYYY-MM-DD.
- lat: Latitude of the location where the catalogs are being generated.
- long: Longitude of the location.
- range: The radius (in kilometers) around the specified latitude/longitude within which catalogs are generated.
- output_dir: The directory where the generated catalogs will be saved. This path is set depending on the operating system (macOS/Linux or Windows).

### 9. Troubleshooting

- **PowerShell Execution Policy (Windows)**:
  If you encounter an error stating that scripts are restricted, the script will attempt to adjust your PowerShell execution policy. If the policy is not changed, run the following command in PowerShell as Administrator:

  ```bash
  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

- **Missing `requirements.txt`**:
  Ensure that the `requirements.txt` file exists in the project root. If not, you may need to create one or manually install the required packages.

- **Error Executing the Script**:
  If you encounter permission issues, ensure you're running PyCharm with appropriate privileges (administrator or elevated user privileges if necessary).

## Conclusion

By following these steps, you can successfully set up your Python environment and run the `catelog_generator.py` script through PyCharm. If you have any issues, feel free to refer to the troubleshooting section or check the terminal output for more detailed error messages.

---