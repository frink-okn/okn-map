# Dockerfile to run rdflib-endpoint

# Start from an official lightweight Python image.
# Using a specific version like 3.9-slim is good practice.
FROM python:3.9-slim


RUN apt-get update && \
    apt-get install -y unzip && \
    rm -rf /var/lib/apt/lists/*
# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first. This step is cached by Docker,
# so dependencies are not re-installed unless the file changes.
COPY requirements.txt .

# Install the Python dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory to hold the TTL data
RUN mkdir /data

# Copy your RDF data file into the container.
# This is the file that the SPARQL endpoint will serve.
# You should replace 'data.ttl' with the name of your actual RDF file.
COPY *.ttl /data

# Expose the port the endpoint will run on.
# The default port for rdflib-endpoint is 8000.
EXPOSE 8000

# Define the command to start the SPARQL endpoint server.
# It's configured to listen on all network interfaces (0.0.0.0)
# and serve the 'data.ttl' file.
CMD ["rdflib-endpoint", "serve", "--host", "0.0.0.0", "--port", "8000", "/data/*.ttl"]
