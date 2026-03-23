# SYSTVETAM — Tower Dashboard Dockerfile
# Zentraux Group LLC
# Stage 1: Build React/Vite app
# Stage 2: Serve via nginx

# --- Build Stage ---
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (cache layer)
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

# Copy source
COPY . .

# VITE_API_URL baked at build time from Railway env var
# Set in Railway: VITE_API_URL=https://your-dispatch.railway.app
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build production bundle
RUN npm run build

# --- Serve Stage ---
FROM nginx:alpine AS runner

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Railway uses dynamic PORT
ENV PORT=3000
EXPOSE 3000

# Substitute PORT in nginx config at runtime
CMD ["sh", "-c", "sed -i "s/\$PORT/$PORT/g" /etc/nginx/conf.d/default.conf && nginx -g "daemon off;""]
