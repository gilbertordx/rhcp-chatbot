# Stage 1: Base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./app ./app

# Expose the port the app runs on
EXPOSE 80

# Command to run the application
# Note: The port in the command should match the one exposed.
# The default port for the app is 3000, but we run it on 80 in the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"] 