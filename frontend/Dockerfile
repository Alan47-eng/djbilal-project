FROM node:18-alpine

WORKDIR /app

# Ensure devDependencies are installed
ENV NODE_ENV=development

COPY package.json ./
RUN npm install --force

COPY . .

EXPOSE 5173

CMD ["npm","run","dev","--","--host","0.0.0.0"]
