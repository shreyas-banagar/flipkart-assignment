# ---- Frontend Dockerfile ----
# Nginx Alpine image to serve static HTML/CSS/JS files
# and proxy /api/* requests to the backend service.

FROM nginx:alpine

# Remove the default Nginx placeholder site
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy custom Nginx config
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy all frontend static files to the Nginx web root
COPY . /usr/share/nginx/html

# Remove the nginx directory from the web root (it only contains config)
RUN rm -rf /usr/share/nginx/html/nginx

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
