# Multi-stage: build TypeScript then run with Node
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run db:generate
RUN npm run build

# Production stage
FROM node:20-bookworm

WORKDIR /app

ENV NODE_ENV=production
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/prisma ./prisma

# Generate Prisma client in final image (uses env at runtime)
RUN npx prisma generate

EXPOSE 3000
CMD ["node", "dist/index.js"]
