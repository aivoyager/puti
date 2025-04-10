FROM python:3.12-slim
WORKDIR /puti

COPY . /puti

RUN apt-get update && apt-get install -y vim && apt-get install -y lsof

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["python","-u", "server.py"]
