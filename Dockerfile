# Base image
FROM python:3.9

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Streamlit needs this to not fail in container
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_PORT=8080
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Expose the port
EXPOSE 8080

# Run the streamlit app
CMD ["streamlit", "run", "TTG.py", "--server.port=8080", "--server.address=0.0.0.0"]
