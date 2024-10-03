import subprocess
import concurrent.futures
import sys
import os
import platform
import shlex
import shutil

def get_main_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()

# Define the paths to the scripts (assuming they are in the same directory as this main script)
main_dir = get_main_dir()

# Define the paths to the scripts
scripts = [
    "airbus_catalog_api.py",
    "capella_master_collector.py",
    "planet_catalog_api.py",
    "skyfi_catalog_api.py"
]

scripts = [os.path.join(main_dir, script) for script in scripts]

params = {
    'start_date': '2020-08-29',
    'end_date': '2020-09-01',
    'lat': 40.7128,
    'long': -74.0060,
    'range': 100.0,
    'output_dir': '/Users/amankhan/Desktop/catalogs' if platform.system() != "Windows" else 'C:\\Users\\amankhan\\Desktop\\catalogs'
}

def check_directory_permissions(output_dir):
    # Check if the directory exists
    if not os.path.exists(output_dir):
        try:
            # Attempt to create the directory
            os.makedirs(output_dir, exist_ok=True)
            print(f"Directory {output_dir} created successfully.")
        except Exception as e:
            print(f"Error creating directory {output_dir}: {e}")
            return False

    # Check if the directory is writable
    if os.access(output_dir, os.W_OK):
        return True
    else:
        print(f"Write permission denied for directory {output_dir}")
        return False

def run_script_in_new_terminal(script_name):
    if not check_directory_permissions(params['output_dir']):
        print(f"Skipping {script_name} due to directory issues.")
        return

    # Construct the command to run the script with parameters
    cmd = [
        sys.executable,  # Use the current Python interpreter
        script_name,
        "--start-date", params['start_date'],
        "--end-date", params['end_date'],
        "--lat", str(params['lat']),
        "--long", str(params['long']),
        "--range", str(params['range']),
        "--output-dir", params['output_dir']
    ]

    # Detect the operating system
    current_os = platform.system()

    try:
        if current_os == "Windows":
            # For Windows, use 'start' to open a new Command Prompt
            # '/k' tells cmd to execute the command and remain open
            # '/c' would execute the command and close
            # The 'start' command needs to be passed as a single string
            cmd_str = ' '.join(shlex.quote(arg) for arg in cmd)
            subprocess.Popen(['start', 'cmd', '/k', cmd_str], shell=True)
        
        elif current_os == "Darwin":
            # For macOS, use AppleScript to open Terminal and execute the command
            script_path = os.path.abspath(script_name)
            cmd_str = ' '.join(shlex.quote(arg) for arg in cmd)
            apple_script = f'''
                tell application "Terminal"
                    do script "{cmd_str}"
                    activate
                end tell
            '''
            subprocess.Popen(['osascript', '-e', apple_script])
        
        elif current_os == "Linux":
            # For Linux, attempt to detect the terminal emulator and use it
            terminal_commands = [
                'gnome-terminal',
                'konsole',
                'xfce4-terminal',
                'xterm',
                'lxterminal',
                'mate-terminal',
                'terminator',
                'tilix',
                'alacritty'  # Added another common terminal emulator
            ]

            # Find which terminal emulator is installed
            terminal = None
            for term in terminal_commands:
                if shutil.which(term):
                    terminal = term
                    break

            if not terminal:
                print("No supported terminal emulator found. Please install one of the following: " +
                      ", ".join(terminal_commands))
                return

            # Construct the command based on the terminal emulator
            if terminal in ['gnome-terminal', 'xfce4-terminal', 'tilix', 'alacritty']:
                # These terminals support the '--' to pass the command
                subprocess.Popen([terminal, '--'] + cmd)
            elif terminal == 'konsole':
                subprocess.Popen([terminal, '-e'] + cmd)
            elif terminal in ['xterm', 'lxterminal', 'mate-terminal', 'terminator']:
                subprocess.Popen([terminal, '-e'] + cmd)
            else:
                print(f"Terminal emulator '{terminal}' is not specifically handled.")
                subprocess.Popen([terminal, '-e'] + cmd)
        
        else:
            print(f"Unsupported operating system: {current_os}")
            return

        print(f"Started {script_name} in a new terminal.")
    except Exception as e:
        print(f"Failed to start {script_name} in a new terminal: {e}")

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(scripts)) as executor:
        futures = [executor.submit(run_script_in_new_terminal, script) for script in scripts]
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    main()
