# Stage 1: Build the React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/neuro-fabric

# Copy package files and install dependencies
COPY neuro-fabric/package*.json ./
RUN npm install

# Copy frontend source and build
COPY neuro-fabric/ ./
RUN npm run build

# Stage 2: Serve the backend API and static frontend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (needed for duckdb/sqlalchemy extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source files
COPY . .

# Ensure empty essential directories exist
RUN mkdir -p data outputs

# Copy compiled frontend from Stage 1 into the location expected by server.py StaticFiles path
COPY --from=frontend-builder /app/neuro-fabric/dist ./neuro-fabric/dist

# Expose port 8000
EXPOSE 8000

# Run the FastAPI server via Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
