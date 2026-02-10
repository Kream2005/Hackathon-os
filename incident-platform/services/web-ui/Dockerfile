# ---- Stage 1: Build ----
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json ./
RUN npm install

COPY . .

ARG VITE_API_GATEWAY_URL=http://localhost:8080
ENV VITE_API_GATEWAY_URL=$VITE_API_GATEWAY_URL

RUN npm run build

# ---- Stage 2: Serve with nginx ----
FROM nginx:alpine

# Copy nginx config for SPA routing
RUN rm /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config: SPA fallback + reverse proxy to API Gateway
RUN cat > /etc/nginx/conf.d/default.conf << 'EOF'
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    # API proxy to gateway
    location /api/ {
        proxy_pass http://api-gateway:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
