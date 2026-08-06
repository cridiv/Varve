# Dockerfile for Varve Next.js Frontend
FROM node:20-alpine AS base

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source files
COPY . .

# Environment variables
ENV PORT=3000
ENV NODE_ENV=development

EXPOSE 3000

CMD ["npm", "run", "dev"]
