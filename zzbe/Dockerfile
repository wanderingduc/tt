FROM python:3

WORKDIR /usr/src/app

RUN pip install fastapi yfinance typing datetime pandas

COPY . .

CMD [ "python", "./main.py" ]
