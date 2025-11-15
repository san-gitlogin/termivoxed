#!/usr/bin/env python3
"""
Setup script for TermiVoxed

This setup.py provides backward compatibility with older Python installations
that don't support pyproject.toml. For modern installations, pyproject.toml
is the preferred configuration file.

Author: Santhosh T
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements from requirements.txt
requirements = []
with open("requirements.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            requirements.append(line)

setup(
    name="termivoxed",
    version="1.0.0",
    author="Santhosh T",
    author_email="",
    description="AI voice-over dubbing tool for content creators - Add professional voice-overs and styled subtitles without recording your own voice",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/san-gitlogin/termivoxed",
    project_urls={
        "Bug Tracker": "https://github.com/san-gitlogin/termivoxed/issues",
        "Documentation": "https://github.com/san-gitlogin/termivoxed#readme",
        "Source Code": "https://github.com/san-gitlogin/termivoxed",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs", "examples"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU AGPL v3 License",
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Video :: Conversion",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
            "black",
            "flake8",
            "mypy",
            "isort",
        ],
        "test": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "termivoxed=main:main",
            "tvx=main:main",
        ],
    },
    include_package_data=True,
    keywords=[
        "video-editor",
        "console",
        "cli",
        "ffmpeg",
        "text-to-speech",
        "tts",
        "subtitles",
        "voice-over",
        "edge-tts",
        "video-processing",
    ],
    license="GNU AGPL v3",
    zip_safe=False,
)
