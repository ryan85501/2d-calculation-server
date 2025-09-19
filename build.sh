#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Install Python dependencies
pip install -r requirements.txt

# Clone the Shwe-Pat-Tee repository into a new subdirectory
echo "Cloning Shwe-Pat-Tee repository..."
git clone https://github.com/ryan85501/Shwe-Pat-Tee.git /opt/render/project/src/shwe-pat-tee

echo "Build complete."
