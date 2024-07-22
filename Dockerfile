# Use the official Python image with the specified version
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install ffmpeg for audio input and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements/requirements.txt requirements/requirements.txt

# Install the dependencies
RUN pip install --no-cache-dir -r requirements/requirements.txt

# Copy the custom index.html to the Streamlit static directory
COPY static/index.html /usr/local/lib/python3.12/site-packages/streamlit/static/index.html

# Copy the rest of the application code into the container
COPY . .


# Expose the port that Streamlit will run on
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "Cora.py"]

