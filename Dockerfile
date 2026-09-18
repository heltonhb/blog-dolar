FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start-dashboard.sh

EXPOSE 5001

ENV FLASK_ENV=production

CMD ["./start-dashboard.sh"]
