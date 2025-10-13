#!/bin/sh

# Set defaults
API_URL=${API_URL:-http://localhost:8000}

# Move nginx config into place
mv /etc/nginx/conf.d/nginx.conf.template /etc/nginx/conf.d/default.conf

# Create config.json with SPARQL endpoint
echo "{\"sparqlEndpoint\":\"${API_URL}\"}" > /usr/share/nginx/html/config.json

exec nginx -g 'daemon off;'