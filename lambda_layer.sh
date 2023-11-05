#!/bin/bash

# Define version variables for Python packages
SELENIUM_VER=3.141.0
SELENIUM_STEALTH_VER=1.0.6
BEAUTIFULSOUP4_VER=4.12.2
BOTO3_VER=1.26.90

# Define runtime variables
RUNTIME=python3.8

# Define the target directory for installations
OUT_DIR=/out/build/chrome_headless/python/lib/$RUNTIME/site-packages

# Function to check and install commands
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "$1 is not installed. Attempting to install..."
        sudo apt-get update
        sudo apt-get install -y "$1"
    else
        echo "$1 is available."
    fi
}

# Check if zip and unzip are available
check_command "zip"
check_command "unzip"

# Install Python packages using pip
docker run -v $(pwd):/out -it lambci/lambda:build-$RUNTIME \
    pip install selenium==$SELENIUM_VER -t $OUT_DIR

# Install additional Python packages
docker run -v $(pwd):/out -it lambci/lambda:build-$RUNTIME \
    pip install selenium_stealth==$SELENIUM_STEALTH_VER beautifulsoup4==$BEAUTIFULSOUP4_VER boto3==$BOTO3_VER -t $OUT_DIR

# Copy the chrome_headless.py, utils.py, and globals.py files
cp chrome_headless.py build/chrome_headless/python/chrome_headless.py
cp utils.py $OUT_DIR
cp globals.py $OUT_DIR

pushd build/chrome_headless

DRIVER_URL=https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VER/chromedriver_linux64.zip
curl -SL $DRIVER_URL >chromedriver.zip
unzip chromedriver.zip
rm chromedriver.zip

# Download chrome binary
CHROME_URL=https://github.com/adieuadieu/serverless-chrome/releases/download/$CHROME_BINARY_VER/stable-headless-chromium-amazonlinux-2017-03.zip
curl -SL $CHROME_URL >headless-chromium.zip
unzip headless-chromium.zip
rm headless-chromium.zip

zip -r ../../chrome_headless.zip *
