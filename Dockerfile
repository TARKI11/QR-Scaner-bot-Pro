# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Install the zbar library (system dependency)
RUN apt-get update && apt-get install -y libzbar0

# 3. Set the working directory in the container
WORKDIR /app

# 4. Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code
COPY . .

# 6. Command to run the application
CMD ["python3", "main.py"]
