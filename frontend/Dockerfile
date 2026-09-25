FROM node:20-alpine

WORKDIR /app

# Install dependencies first (leverage Docker caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the frontend application code
COPY . .

# Expose Vite's default dev server port
EXPOSE 5173

# Run the dev server, binding to 0.0.0.0 to allow access outside the container
CMD ["npm", "run", "dev", "--", "--host"]
