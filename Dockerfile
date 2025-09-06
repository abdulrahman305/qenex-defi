# QENEX OS Docker Image
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY hardhat.config.js ./

# Install dependencies
RUN npm ci --only=production 2>/dev/null || npm install

# Copy contracts and scripts
COPY contracts ./contracts
COPY scripts ./scripts
COPY test ./test

# Compile contracts
RUN npx hardhat compile

# Expose Hardhat node port
EXPOSE 8545

# Default command runs local node
CMD ["npx", "hardhat", "node"]
