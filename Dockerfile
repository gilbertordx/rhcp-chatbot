FROM node:18-slim as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci
COPY . .

FROM node:18-slim

WORKDIR /app

COPY --from=builder /app/package*.json ./
COPY --from=builder /app/src ./src
COPY --from=builder /app/node_modules ./node_modules

ENV NODE_ENV=production

CMD ["node", "src/app.js"]

