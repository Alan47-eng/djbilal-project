FROM node:18-alpine

WORKDIR /app

ENV NODE_ENV=development

COPY package*.json ./
RUN npm install --force

COPY . .

RUN npm run build

EXPOSE 4173

CMD ["sh", "-c", "printf 'window.__ENV__ = { VITE_API_BASE_URL: \"%s\" };\\n' \"${VITE_API_BASE_URL:-http://localhost:8000}\" > dist/env.js && npm run start -- --port ${PORT:-4173}"]
