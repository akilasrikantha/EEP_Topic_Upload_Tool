import os
import shutil


def ensure_directory_exists(directory_path):
    """
    Ensure that a directory exists, creating it if necessary
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def copy_file(source, destination):
    """
    Copy a file from source to destination, ensuring the destination directory exists
    """
    ensure_directory_exists(os.path.dirname(destination))
    shutil.copy2(source, destination)


def remove_directory(directory_path, ignore_errors=False):
    """
    Remove a directory and all its contents
    """
    if os.path.exists(directory_path):
        shutil.rmtree(directory_path, ignore_errors=ignore_errors)


def file_exists_with_pattern(directory, pattern):
    """
    Check if a file exists in the directory that matches the given regex pattern
    """
    import re
    if not os.path.exists(directory):
        return False

    for file in os.listdir(directory):
        if re.match(pattern, file):
            return os.path.join(directory, file)

    return None