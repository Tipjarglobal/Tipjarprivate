FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir telethon pymongo python-dotenv requests beautifulsoup4 lxml twikit
COPY . .
CMD ["python", "-u", "main.py"]
