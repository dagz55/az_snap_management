import os
import subprocess
import sys
import curses
import venv

def check_az_cli():
    if subprocess.run(["command", "-v", "az"], capture_output=True, text=True).returncode != 0:
        print("Azure CLI is not installed. Please install Azure CLI and try again.")
        sys.exit(1)

def check_az_login():
    if subprocess.run(["az", "account", "show"], capture_output=True, text=True).returncode != 0:
        print("Azure CLI is not logged in. Please log in and try again.")
        sys.exit(1)

def setup_venv():
    venv_dir = "snapvenv"
    if not os.path.isdir(venv_dir):
        venv.create(venv_dir, with_pip=True)
    
    # Get the path to the activated virtual environment's Python
    if sys.platform == "win32":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
    
    # Install or upgrade pip and packages
    subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"])

def validate_snapshots():
    venv_python = get_venv_python()
    subprocess.run([venv_python, "validate_snapshot.py"])

def create_snapshots():
    venv_python = get_venv_python()
    subprocess.run([venv_python, "create_snapshot.py"])

def delete_snapshots():
    venv_python = get_venv_python()
    subprocess.run([venv_python, "delete_snapshot.py"])

def install_packages():
    venv_python = get_venv_python()
    subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"])
    print("All packages and pip updated successfully.")

def get_venv_python():
    venv_dir = "snapvenv"
    if sys.platform == "win32":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        return os.path.join(venv_dir, "bin", "python")

def draw_menu(stdscr, selected_row_idx):
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    for idx, row in enumerate(menu):
        x = w//2 - len(row)//2
        y = h//2 - len(menu)//2 + idx
        if idx == selected_row_idx:
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(y, x-2, "> ")
            stdscr.addstr(y, x, row)
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(y, x, row)
    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

    current_row = 0

    while True:
        draw_menu(stdscr, current_row)

        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu)-1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == len(menu)-1:
                break
            stdscr.clear()
            stdscr.refresh()
            curses.endwin()
            if current_row == 0:
                create_snapshots()
            elif current_row == 1:
                validate_snapshots()
            elif current_row == 2:
                delete_snapshots()
            elif current_row == 3:
                install_packages()
            stdscr.getch()

if __name__ == "__main__":
    check_az_cli()
    check_az_login()
    setup_venv()

    menu = [
        "1. Create Snapshots",
        "2. Validate Snapshots",
        "3. Delete Snapshots",
        "4. Install Required Packages and Update pip",
        "5. Quit"
    ]

    curses.wrapper(main)