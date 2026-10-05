FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py contacts.json ./
COPY templates ./templates
ENV PORT=8088
EXPOSE 8088
CMD ["python", "app.py"]
