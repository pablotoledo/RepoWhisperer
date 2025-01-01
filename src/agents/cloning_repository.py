import os
import subprocess

def clone_repository():
    repo_url = input("Please enter the repository URL to clone: ")
    clone_dir = "coding/repository"
    
    # Create the directory if it doesn't exist
    os.makedirs(clone_dir, exist_ok=True)
    
    try:
        subprocess.run(["git", "clone", repo_url, clone_dir], check=True)
        print("Repository cloned successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
