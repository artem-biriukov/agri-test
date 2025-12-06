FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

# Set build-time environment variables
ENV NEXT_PUBLIC_API_URL=http://34.117.183.74/api
ENV NEXT_PUBLIC_RAG_URL=http://34.117.183.74/api

# Build the app (this bakes env vars into the JS bundle)
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
