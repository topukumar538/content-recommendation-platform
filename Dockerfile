FROM python:3.12-slim

# set working directory
WORKDIR /app

# install dependencies first (cached layer)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy backend code
COPY backend/ ./backend/

# copy frontend
COPY frontend/ ./frontend/

# set working directory to backend for uvicorn
WORKDIR /app/backend

# expose port
EXPOSE 8000

# run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]