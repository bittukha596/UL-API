# Use a lightweight Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual script
COPY app.py .

# Open port 8000 for the API
EXPOSE 8000

# Fire the engine!
CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "8000"]
