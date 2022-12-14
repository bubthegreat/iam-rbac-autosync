FROM python:3.7

ADD ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

ADD ./src /src
CMD kopf run /src/handlers/handler.py
