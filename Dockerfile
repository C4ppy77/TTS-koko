# Dockerfile
# Use an official Python runtime as a parent image.
# We'll use a specific version based on Debian Bookworm for stability.
FROM python:3.9-slim-bookworm

# Set environment variables for non-interactive apt-get operations
ENV DEBIAN_FRONTEND=noninteractive
# Often helpful for ensuring text processing works correctly
ENV PYTHONIOENCODING=UTF-8

# Set the working directory in the container.
# All subsequent commands will run from this directory.
WORKDIR /app

# Install any necessary system dependencies required for building Python packages.
# 'build-essential' package includes compilers (like gcc) and other build tools.
# git is useful for cloning repositories, although not strictly needed if all code is COPIED.
# We keep build-essential as some packages might still need it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    # Add espeak-ng which is required by kokoro for phonemization if not using a spaCy model
    # Although misaki seems to be using spaCy, having espeak-ng might be a fallback or requirement.
    espeak-ng \
    && rm -rf /var/lib/apt/lists/* # Clean up to reduce image size

# Copy the current directory contents into the container at /app.
# This includes your api.py, requirements.txt, the kokoro folder, etc.
COPY . /app

# Install the required Python packages from requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# --- Add step to download spaCy language model ---
# This step uses the spaCy CLI to download the required model during the build.
# We assume 'en_core_web_sm' is the model misaki/kokoro expects.
# If this still fails, you might need to consult misaki/kokoro documentation
# or source code to determine the exact required spaCy model name.
RUN python -m spacy download en_core_web_sm --direct

# Expose the port the application will listen on.
EXPOSE 5000

# Define the command to run your application using Gunicorn.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "api:app"]