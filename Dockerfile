# Stage 1: Build frontend
FROM --platform=$BUILDPLATFORM node:alpine AS builder-frontend
WORKDIR /app
RUN npm i -g pnpm
COPY pnpm-lock.yaml package.json ./
RUN pnpm i
COPY . .
RUN pnpm build \
  # remove source maps - people like small image
  && rm public/*.map || true

# Stage 2: Prepare Python backend and final image
FROM python:3.9-alpine

# Copy Nginx configuration files
COPY docker/default.conf /etc/nginx/conf.d/default.conf
COPY docker/nginx.conf /etc/nginx/nginx.conf

WORKDIR /app

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Nginx and other utilities
RUN apk add --no-cache nginx dos2unix

# Copy and install Python dependencies
COPY python/ .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create Clash config directory (if still needed by the python app from Dockerfile-python)
RUN mkdir -p /root/.config/clash

# Remove default Nginx content and copy built frontend assets
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder-frontend /app/public /usr/share/nginx/html

# Set default backend URL for YACD (can be overridden at runtime)
ENV YACD_DEFAULT_BACKEND "http://127.0.0.1:9090"

# Expose Nginx port (80) and Python app port (e.g., 7888 from Dockerfile-python)
EXPOSE 80
EXPOSE 7888

# Copy and prepare entrypoint script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh && dos2unix /docker-entrypoint.sh

# Command to run the entrypoint script
CMD ["/docker-entrypoint.sh"]