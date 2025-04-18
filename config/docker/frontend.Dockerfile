# Use an official Node.js runtime as the base image
FROM node:23.11-alpine AS base

# Set working directory
WORKDIR /app

# Copy package.json and yarn.lock
COPY frontend/package.json frontend/yarn.lock ./

# Install dependencies
RUN yarn install

# Copy the rest of the application code
COPY frontend/ .

FROM base as development

EXPOSE 3000

CMD ["yarn", "run", "dev"]


FROM base AS production
# Build the application
RUN yarn build

# Expose the port Vite preview uses
EXPOSE 4173

# Use Vite's production-ready preview server
CMD ["yarn", "preview"]
