FROM python:3.11-slim

# Create a non-root user 'user' with UID 1000
RUN useradd -m -u 1000 user

WORKDIR /home/user/app

COPY backend/requirements.txt ./backend/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=user:user backend/ ./backend/
COPY --chown=user:user frontend/ ./frontend/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user

# Switch to the non-root user
USER user

WORKDIR /home/user/app/backend

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "debug"]