FROM node:20-slim

# Set working directory
WORKDIR /usr/src/app

# Install build dependencies and Angular CLI
RUN apt-get update && apt-get install -y python3 make g++ && \
    npm install -g @angular/cli@17.3.17 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy package files separately for better caching
COPY package*.json ./

# Install dependencies
RUN npm install --force

# Copy remaining project files
COPY . .

# Accept ENV_NAME as build argument (default: local)
ARG ENV_NAME=local

# Replace the environment file based on ENV_NAME
RUN cp projects/agentic-chatbot/src/environments/environment.${ENV_NAME}.ts \
        projects/agentic-chatbot/src/environments/environment.ts

# Increase memory for Angular builds
ENV NODE_OPTIONS="--max-old-space-size=12288"

# Expose the default Angular port
EXPOSE 4200

# Start the Angular dev server
CMD ["ng", "serve", "agentic-chatbot", "--host", "0.0.0.0", "--disable-host-check"]
