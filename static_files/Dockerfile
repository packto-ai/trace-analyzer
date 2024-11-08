# Use an official Python runtime as a parent image
FROM python:3.12.4

#Prevents Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /static_files

# Copy static files
COPY . /static_files

# Expose port 8009
EXPOSE 8009

# Run Python HTTP server for static files
CMD ["python3", "-m", "http.server", "8009"]