FROM python:3.11-slim
WORKDIR /app
COPY requirements-docker.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p instance
EXPOSE 5001
ENV FLASK_APP=app.py
ENV FLASK_ENV=development
ENV PYTHONUNBUFFERED=1
CMD ["python", "app.py"]