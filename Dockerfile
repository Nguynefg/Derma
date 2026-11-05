FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements/base.txt backend/requirements/constraints.txt ./
RUN pip install --no-cache-dir -r base.txt
COPY backend/app ./app
COPY --from=frontend /frontend/dist /frontend/dist
ENV FRONTEND_DIST=/frontend/dist DATA_DIR=/app/data
RUN useradd --create-home derma && mkdir /app/data && chown derma:derma /app/data
USER derma
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
