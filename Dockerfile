# Base image
FROM python:3.10

# Working directory inside container
WORKDIR /app

# Copy all files from your local to container
COPY . /app

# Install required packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Streamlit runs on
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "TTG.py", "--server.port=8501", "--server.enableCORS=false"]
