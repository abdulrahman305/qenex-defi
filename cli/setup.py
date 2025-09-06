"""Setup script for QENEX OS CLI"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="qenex-cli",
    version="5.0.0",
    author="QENEX Team",
    author_email="support@qenex.ai",
    description="CLI for QENEX Unified AI Operating System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/abdulrahman305/qenex-os",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.28.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "websocket-client>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "qenex=qenex_cli.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "qenex_cli": ["templates/*.yaml", "configs/*.json"],
    },
)