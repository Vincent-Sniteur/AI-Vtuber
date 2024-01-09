import shutil
import os

def backup_files(file_paths, destination_directory):
    # Check if the destination directory exists, create it if not
    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)

    for source_file_path in file_paths:
        # Check if the source file exists
        if os.path.exists(source_file_path):
            # Get the file name
            file_name = os.path.basename(source_file_path)

            # Build the destination file path
            destination_file_path = os.path.join(destination_directory, file_name)

            # Check if the destination file exists, delete if it does
            if os.path.exists(destination_file_path):
                os.remove(destination_file_path)

            # Copy the file, overwriting if it already exists
            shutil.copy2(source_file_path, destination_file_path)
            print(f"File '{file_name}' backed up to '{destination_directory}'")
        else:
            print(f"File '{source_file_path}' not found. Skipping.")

def backup_dir(source_path, destination_directory):
    # Check if the destination directory exists, create it if not
    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)

    # Build the destination path
    destination_path = os.path.join(destination_directory, os.path.basename(source_path))

    try:
        # Check if the source path is a file or directory
        if os.path.isfile(source_path):
            # If it's a file, check if the destination file exists, delete if it does
            if os.path.exists(destination_path):
                os.remove(destination_path)

            # Use shutil.copy2 for file copy
            shutil.copy2(source_path, destination_path)
            print(f"File '{source_path}' backed up to '{destination_directory}'")
        elif os.path.isdir(source_path):
            # If it's a directory, check if the destination directory exists, delete if it does
            if os.path.exists(destination_path):
                shutil.rmtree(destination_path)

            # Use shutil.copytree for directory copy
            shutil.copytree(source_path, destination_path)
            print(f"Folder '{source_path}' backed up to '{destination_directory}'")
        else:
            print(f"Unsupported source type: '{source_path}'")
    except Exception as e:
        print(f"Error during backup: {e}")

# Get the absolute path of the current script's directory
current_directory = os.path.abspath(os.path.dirname(__file__))
# Example usage
file_paths_to_backup = [
    os.path.join(current_directory, "config.json")
]
dir_path_to_backup = os.path.join(current_directory, "data")
dir_path_to_backup2 = os.path.join(current_directory, "out")

destination_directory_path = os.path.join(current_directory, "backup")  # Replace with the actual backup directory path

backup_files(file_paths_to_backup, destination_directory_path)
backup_dir(dir_path_to_backup, destination_directory_path)
backup_dir(dir_path_to_backup2, destination_directory_path)

print("Execution completed")
