#!/bin/sh
# Replace backend URL in index.html
sed -i "s|http://127.0.0.1:9090|$YACD_DEFAULT_BACKEND|" /usr/share/nginx/html/index.html

# Start Python application in the background
# The WORKDIR in the final Docker image is /app, and the python app is copied there.
python app.py &

# Start Nginx in the foreground
nginx -g "daemon off;"
