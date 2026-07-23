FROM node:20

# Set working directory
WORKDIR /app

# Copy package lists first for layer caching
COPY package*.json ./

# Install packages
RUN npm install --omit=dev


# Copy application source
COPY index.js ./

# Set environment defaults
ENV PORT=3000
ENV ODOO_WEBHOOK_URL=http://odoo:8069/api/whatsapp/webhook

# Expose microservice port
EXPOSE 3000

# Run service
CMD ["node", "index.js"]
