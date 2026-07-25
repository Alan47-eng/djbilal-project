FROM node:18-alpine

WORKDIR /app

# Ensure devDependencies (vite) are installed for the dev server
ENV NODE_ENV=development

COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY . .

EXPOSE 5173

CMD ["npm","run","dev","--","--host","0.0.0.0"]
