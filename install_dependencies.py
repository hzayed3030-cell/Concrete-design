import os
import sys
import subprocess

def install_requirements(req_file="requirements.txt"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    req_path = os.path.join(base_dir, req_file)

    if not os.path.exists(req_path):
        print(f"File not found: {req_path}")
        return

    with open(req_path, "r", encoding="utf-8") as f:
        packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Found {len(packages)} packages to install: {', '.join(packages)}\n")

    for package in packages:
        print(f"==================================================")
        print(f"Installing: {package}")
        print(f"Command: {sys.executable} -m pip install {package}")
        print(f"==================================================")
        result = subprocess.run([sys.executable, "-m", "pip", "install", package])
        if result.returncode == 0:
            print(f"Successfully installed {package}\n")
        else:
            print(f"Failed to install {package} (Exit code: {result.returncode})\n")

if __name__ == "__main__":
    install_requirements()
