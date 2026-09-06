FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/console/package*.json ./
RUN npm install

COPY frontend/console/ ./
RUN npm run build

FROM nginx:alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]

