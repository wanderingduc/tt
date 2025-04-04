FROM python:3

WORKDIR /usr/src/app

RUN pip install -r ./requirements.txt

COPY . .

CMD [ "python", "./main.py" ]
