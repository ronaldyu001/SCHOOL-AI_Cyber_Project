# Build
FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build


# Runtime
FROM nginx:alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
# Serves the SPA fallback and proxies /api to the backend service.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
