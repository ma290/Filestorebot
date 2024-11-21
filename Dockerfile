# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Create the video directory in the container
RUN mkdir -p videos/

# Expose port (optional if you have a webhook setup; otherwise, it is ignored for polling)
EXPOSE 8443

# Run the bot
CMD ["python", "bot.py"]