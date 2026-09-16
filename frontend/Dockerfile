FROM node:20-alpine AS build
WORKDIR /app
COPY package.json vite.config.ts tsconfig.json index.html ./
COPY src/ ./src/
RUN npm ci && npm run build
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
