FROM python:3.10.0-slim-bullseye
WORKDIR /usr/app
COPY ./requirements.txt .
RUN python3 -m pip install -r requirements.txt
COPY ./wait-for-it.sh /usr/bin/wait-for-it.sh
EXPOSE 8080
