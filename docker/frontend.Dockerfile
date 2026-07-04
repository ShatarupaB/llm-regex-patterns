# ── React / Vite dev server ───────────────────────────────────────────────────
# Production: swap `npm run dev` for `npm run build` + serve with nginx.
# ─────────────────────────────────────────────────────────────────────────────

FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

# Vite needs --host so the dev server is reachable from outside the container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
