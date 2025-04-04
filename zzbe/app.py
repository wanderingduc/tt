from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
from datetime import datetime as dt

app = FastAPI()

origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_methods = ['GET']
)


@app.get("/")
def read_root():
    return {"Hello":"World"}

@app.get("/anal/")
def get_anal():

    full = {
        'data': [],
        'meta': {
            'timestamp': dt.now()
        }
    }
    exchange = 'OL'

    with open('agg.txt', 'r', encoding='UTF-8') as file:
        data = file.read()
        data = data.split('\n')
        for line in data:
            line = line.split(';')
            if not line[-1] =='':
                c = line[-1].split('-')[-2].upper()
                if len(c) > 6:
                    c = c.split('/')[-1]
                # full['data'].append(c)
                ticker = f'{c}.{exchange}'
                # print(ticker)
                dat = yf.Ticker(ticker)
                h = dat.history(period = '12mo')
                cur = h['Close'].array
                prev = h["Close"].array[:-1]
                ret = calc_anal(cur, prev, c)
                if ret['cross']['two'] or ret['cross']['one']:
                    full['data'].append(ret)


    return full

def calc_anal(prices, prev_prices, ticker):

    anal = {'ticker':ticker,
            'old':None,
            'new':None,
            'cross':{
                'two':None,
                'one':None 
            }
            }

    pda = pd.Series(prices)
    p_pda = pd.Series(prev_prices)
    sma200 = pda.tail(200).mean() if len(pda) >= 200 else None
    p_sma200 = p_pda.tail(200).mean()  if len(p_pda) >= 200 else None
    sma100 = pda.tail(100).mean() if len(pda) >= 100 else None
    p_sma100 = p_pda.tail(100).mean() if len(p_pda) >= 100 else None
    # ema100 = pda.tail(100).ewm(span=100, adjust=False).mean().iloc[-1]
    ema100 = 0
    # p_ema100 = p_pda.tail(100).ewm(span=100, adjust=False).mean().iloc[-1]
    p_ema100 = 0
    ema50 = pda.tail(50).ewm(span=50, adjust=False).mean().iloc[-1] if len(pda) >= 50 else None
    p_ema50 = p_pda.tail(50).ewm(span=50, adjust=False).mean().iloc[-1] if len(p_pda) >= 50 else None

    anal['old'] = {
                'sma200':p_sma200,
                'sma100':p_sma100,
                'ema100':p_ema100,
                'ema50':p_ema50
            }
    
    anal['new'] = {
                'sma200':sma200,
                'sma100':sma100,
                'ema100':ema100,
                'ema50':ema50
            }

    # print(round(sma200, 2))
    # print(round(p_sma200, 2))
    # print(round(sma100, 2))
    # print(round(p_sma100, 2))
    # print(round(ema100, 2))
    # print(round(p_ema100, 2))
    # print(round(ema50, 2))
    # print(round(p_ema50, 2))

    # print("sma200 vs ema50")
    if sma200 and sma100 and ema50 and p_sma200 and p_sma100 and p_ema50:
        if sma200 > ema50:
            if p_sma200 < p_ema50:
                anal['cross']['two'] = 'Gold'
                # print("Gold cross")
        if sma200 < ema50:
            if p_sma200 > p_ema50:
                anal['cross']['two'] = 'Death'
                # print("Death cross")
        # print("sma100 vs ema50")
        if sma100 > ema50:
            if p_sma100 < p_ema50:
                anal['cross']['one'] = 'Gold'
                # print("Gold cross")
        if sma100 < ema50:
            if p_sma100 > p_ema50:
                anal['cross']['one'] = 'Death'
                # print("Death cross")

    return anal    
