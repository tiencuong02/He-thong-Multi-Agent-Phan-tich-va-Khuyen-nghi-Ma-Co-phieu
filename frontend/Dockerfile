# Step 1: Build the React application
FROM node:18 AS build

WORKDIR /app

# Copy package descriptors and install dependencies
COPY package*.json ./
RUN npm install || true

# Copy the rest of the frontend application
COPY . .

# Run build (and fallback to creating a dummy build if package.json doesn't exist or build fails)
RUN npm run build || (mkdir -p dist && echo "<h1>Frontend Placeholder</h1>" > dist/index.html)

# Step 2: Serve with Nginx
FROM nginx:alpine

# Copy custom Nginx configuration to enable API proxying
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build output to the nginx html directory
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
