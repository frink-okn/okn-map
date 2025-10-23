FROM node:alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG PUBLIC_URL=__PUBLIC_URL_PLACEHOLDER__
ENV PUBLIC_URL=${PUBLIC_URL}
ENV VITE_BASE_PATH=/
RUN npx vite build

FROM nginx:alpine
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html
COPY docker-frontend/startup.sh /docker-entrypoint.d/
COPY docker-frontend/nginx.conf.template /etc/nginx/conf.d/

RUN chmod -R 755 /usr/share/nginx/html && \
    chmod +x /docker-entrypoint.d/startup.sh

EXPOSE 8080
CMD ["sh", "-c", "/docker-entrypoint.d/startup.sh"]