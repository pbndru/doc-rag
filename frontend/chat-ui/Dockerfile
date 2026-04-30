# Use an official Node runtime as a build stage
FROM node:20-alpine AS build
WORKDIR /app
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
COPY package.json ./
RUN npm install
COPY . ./
RUN npm run build

# Production stage – serve with a static server
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 3000
# Ensure the API URL is embedded in the built files. React reads REACT_APP_API_URL at build time.
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
CMD ["nginx", "-g", "daemon off;"]
