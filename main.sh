#!/bin/bash

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to create and activate virtual environment
setup_venv() {
    if [ ! -d "snapvenv" ]; then
        python -m venv snapvenv
    else
        source snapvenv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    fi
}

# Function to validate snapshots
validate_snapshots() {
    # Run the Python script
    python "$SCRIPT_DIR/validate_snapshot.py"
}

# Function to create snapshots
create_snapshots() {
    python "$SCRIPT_DIR/create_snapshot.py"
}

# Function to delete snapshots
delete_snapshots() {
    python "$SCRIPT_DIR/delete_snapshot.py"
}


# Main menu loop
while true; do
    echo "Snapshot Management Menu"
    echo "1. Create Snapshots"
    echo "2. Validate Snapshots"
    echo "3. Delete Snapshots"
    echo "4. Exit"
    read -p "Please enter your choice (1-4): " choice

    case $choice in
        1)
            create_snapshots
            ;;
        2)
            validate_snapshots
            ;;
        3)
            delete_snapshots
            ;;
        4)
            echo "Exiting..."
            deactivate
            exit 0
            ;;
        *)
            echo "Invalid option. Please try again."
            ;;
    esac

    echo
done

