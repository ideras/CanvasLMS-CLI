#!/usr/bin/env python3
"""
Setup script for Canvas LMS CLI
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="canvas-lms-cli",
    version="1.0.0",
    author="Canvas LMS CLI Contributors",
    author_email="",
    description="A powerful command-line interface for managing Canvas LMS courses, students, assignments, and grade uploads",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/CanvasLMS-CLI",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Topic :: Education",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=read_requirements(),
    entry_points={
        'console_scripts': [
            'canvas-cli=canvas_cli:main',
        ],
    },
    keywords="canvas lms education cli grading students assignments",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/CanvasLMS-CLI/issues",
        "Source": "https://github.com/yourusername/CanvasLMS-CLI",
        "Documentation": "https://github.com/yourusername/CanvasLMS-CLI#readme",
    },
    include_package_data=True,
    zip_safe=False,
)