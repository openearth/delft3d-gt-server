FROM python:3.10-slim-buster
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY . /app
WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     kubectl && \
#     rm -rf /var/lib/apt/lists/*
# RUN wget https://amazon-eks.s3.us-west-2.amazonaws.com/1.18.9/2020-11-02/bin/linux/amd64/aws-iam-authenticator

RUN pip install -r requirements.txt
# RUN pip install awscli
