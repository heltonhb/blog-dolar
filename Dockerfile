# 3.11 is the floor for the whole project: CI lints and tests at this version
# and ruff targets py311, so a container on a different minor could accept (or
# reject) syntax the other side disagrees with. See .python-version.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start-dashboard.sh

EXPOSE 5001

ENV FLASK_ENV=production

CMD ["./start-dashboard.sh"]
