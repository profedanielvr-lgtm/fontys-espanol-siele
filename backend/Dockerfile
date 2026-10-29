FROM python:3.12-slim
WORKDIR /project
COPY backend/requirements.lock.txt ./backend/requirements.lock.txt
RUN pip install --no-cache-dir -r backend/requirements.lock.txt
COPY backend/app ./backend/app
COPY frontend/public/bank.json ./frontend/public/bank.json
WORKDIR /project/backend
RUN useradd --create-home app && mkdir /data && chown app:app /data
USER app
ENV DATABASE_URL=sqlite:////data/simulador.db UPLOAD_DIR=/data/uploads
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
