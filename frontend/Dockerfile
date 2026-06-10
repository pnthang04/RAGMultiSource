FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json
COPY tsconfig.json /app/tsconfig.json
COPY next.config.mjs /app/next.config.mjs
COPY next-env.d.ts /app/next-env.d.ts
COPY app /app/app
COPY components /app/components
COPY features /app/features
COPY hooks /app/hooks
COPY lib /app/lib
COPY types /app/types

RUN npm install
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-p", "3000"]
