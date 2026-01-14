#!/usr/bin/env python3
"""
Setup script for cloud-billing-automation package.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="cloud-billing-automation",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    description="DevOps-centric cloud cost governance and automation tool",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="H A R S H H A A",
    author_email="contact@example.com",
    url="https://github.com/NotHarshhaa/cloud-billing-automation",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "cloud_billing_automation": [
            "templates/*.jinja2",
            "config/*.yaml",
        ]
    },
    install_requires=read_requirements(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "cba=cloud_billing_automation.cli.main:app",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
        "Topic :: Office/Business :: Financial",
    ],
    keywords="cloud billing devops cost automation finops",
    project_urls={
        "Documentation": "https://github.com/NotHarshhaa/cloud-billing-automation/docs",
        "Source": "https://github.com/NotHarshhaa/cloud-billing-automation",
        "Tracker": "https://github.com/NotHarshhaa/cloud-billing-automation/issues",
    },
)
