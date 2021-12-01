FROM python:3.8.12-slim-bullseye
WORKDIR /usr/app
COPY ./requirements.txt .
RUN python3 -m pip install -r requirements.txt
EXPOSE 8443
