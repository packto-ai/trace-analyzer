# Use an official Python runtime as a parent image
FROM python:3.12.4

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Upgrade pip before installing requirements
RUN pip install --upgrade pip

# Increase timeout and retry limits
RUN pip install -r requirements.txt --retries 10 --timeout 60

# Copy the rest of the application code to the container
COPY . .

# Set environment variables (if using an env file, this can be done via docker-compose)
# Alternatively, you can copy and source the env file here if needed
# COPY keys.env .env
# ENV $(cat .env | xargs)

# Ensure the /app directory and subdirectories have the correct permissions
RUN chmod -R 755 /app

# Expose the port that the app runs on
EXPOSE 8000

ENV PYTHONPATH=/app/src

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]