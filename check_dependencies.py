#!/usr/bin/env python3
"""
TermiVoxed - Dependency Checker
Author: Santhosh T

This script checks all dependencies required for the TermiVoxed.
"""

import sys
import subprocess
import platform
from pathlib import Path


def print_header(text):
    """Print a formatted header"""
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)
    print()


def print_check(name, status, message=""):
    """Print a check result"""
    symbol = "✓" if status else "✗"
    color = "\033[92m" if status else "\033[91m"  # Green or Red
    reset = "\033[0m"

    print(f"{color}{symbol}{reset} {name:<30} {message}")


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    required_major, required_minor = 3, 8

    is_valid = version.major >= required_major and version.minor >= required_minor
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if is_valid:
        print_check("Python", True, f"v{version_str}")
    else:
        print_check("Python", False, f"v{version_str} (requires >= 3.8)")

    return is_valid


def check_command(command, name):
    """Check if a command is available"""
    try:
        result = subprocess.run(
            [command, "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Extract version from output
            version_line = result.stdout.split('\n')[0] if result.stdout else ""
            print_check(name, True, version_line[:50])
            return True
        else:
            print_check(name, False, "Not found or error")
            return False

    except FileNotFoundError:
        print_check(name, False, "Not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print_check(name, False, "Command timed out")
        return False
    except Exception as e:
        print_check(name, False, str(e)[:40])
        return False


def check_python_package(package_name):
    """Check if a Python package is installed"""
    try:
        __import__(package_name.replace("-", "_"))
        print_check(package_name, True, "Installed")
        return True
    except ImportError:
        print_check(package_name, False, "Not installed")
        return False


def check_all_python_packages():
    """Check all required Python packages from requirements.txt"""
    requirements_file = Path(__file__).parent / "requirements.txt"

    if not requirements_file.exists():
        print("⚠ requirements.txt not found")
        return False

    packages = []
    with open(requirements_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Extract package name (before any version specifier)
                package = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                packages.append(package)

    all_installed = True
    for package in packages:
        if not check_python_package(package):
            all_installed = False

    return all_installed


def get_installation_instructions():
    """Get platform-specific installation instructions"""
    system = platform.system().lower()

    instructions = {
        "darwin": {  # macOS
            "ffmpeg": "brew install ffmpeg",
            "python": "brew install python3",
        },
        "linux": {
            "ffmpeg": "sudo apt-get install ffmpeg  (Debian/Ubuntu)\n" +
                     "                                    sudo dnf install ffmpeg      (Fedora)\n" +
                     "                                    sudo pacman -S ffmpeg        (Arch)",
            "python": "sudo apt-get install python3 python3-pip",
        },
        "windows": {
            "ffmpeg": "choco install ffmpeg  (using Chocolatey)\n" +
                     "                                    scoop install ffmpeg (using Scoop)\n" +
                     "                                    Or download from: https://ffmpeg.org/download.html",
            "python": "Download from: https://www.python.org/downloads/",
        },
    }

    return instructions.get(system, instructions["linux"])


def main():
    """Main dependency checker"""
    print_header("TermiVoxed - Dependency Checker")

    # System Information
    print(f"Platform:   {platform.platform()}")
    print(f"System:     {platform.system()} {platform.release()}")
    print(f"Machine:    {platform.machine()}")

    # Check Python
    print_header("Core Requirements")
    python_ok = check_python_version()

    # Check FFmpeg
    ffmpeg_ok = check_command("ffmpeg", "FFmpeg")
    ffprobe_ok = check_command("ffprobe", "FFprobe")

    # Check Python packages
    print_header("Python Packages")
    packages_ok = check_all_python_packages()

    # Summary
    print_header("Summary")

    all_ok = python_ok and ffmpeg_ok and ffprobe_ok and packages_ok

    if all_ok:
        print("\033[92m✓ All dependencies are installed!\033[0m")
        print()
        print("You can run the application with:")
        print("  python main.py")
        print()
        return 0
    else:
        print("\033[91m✗ Some dependencies are missing.\033[0m")
        print()

        # Provide installation instructions
        instructions = get_installation_instructions()

        if not python_ok:
            print(f"Install Python: {instructions['python']}")
            print()

        if not (ffmpeg_ok and ffprobe_ok):
            print(f"Install FFmpeg: {instructions['ffmpeg']}")
            print()

        if not packages_ok:
            print("Install Python packages:")
            print("  pip install -r requirements.txt")
            print()
            print("Or run the setup script:")
            system = platform.system().lower()
            if system == "windows":
                print("  setup.bat      (Command Prompt)")
                print("  .\\setup.ps1    (PowerShell)")
            else:
                print("  ./setup.sh")
            print()

        return 1


if __name__ == "__main__":
    sys.exit(main())
