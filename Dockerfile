FROM python:3.12-slim
WORKDIR /puti

COPY . /puti

RUN apt-get update && \
    apt-get install -y vim lsof curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

EXPOSE 8000

CMD ["python","-u", "main.py"]
