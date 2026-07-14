FROM node:20

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .

RUN npm run build

RUN npm install -g serve

USER node
CMD ["serve", "-s", "dist", "-l", "3000"]