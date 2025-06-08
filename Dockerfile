FROM python:3.10-slim

RUN apt-get update && apt-get install -y build-essential python3-dev \
    && pip install pyinstaller

WORKDIR /app
COPY . /app

RUN pyinstaller --onefile OPRDatacard.py --add-data ./data:./data