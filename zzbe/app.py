from typing import Union
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
from datetime import datetime as dt, timezone as tz
from zoneinfo import ZoneInfo
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()

host = os.getenv("HOST")
user = os.getenv("USER")
password = os.getenv("PASSWORD")
db = os.getenv("DB")

def after_close():
    h = dt.now(ZoneInfo("Europe/Oslo")).hour
    m = dt.now(ZoneInfo("Europe/Oslo")).minute

    if h >= 16 and m >= 30:
        return True
    return False

def connect_to_mysql(host, user, password, database):
    try:
        # Establish the connection
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        
        if connection.is_connected():
            print("Successfully connected to the database")
            return connection
        else:
            print("Connection failed")
            return None

    except Error as e:
        print(f"Error: {e}")
        return None

app = FastAPI()

origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_methods = ['GET']
)

class Stocks:
    stocks: list | None = None

@app.get("/health/")
def health():
    return {'host':host,'user':user,'password':password,'db':db}


@app.get("/")
def read_root():
    return {"Hello":"World"}

@app.get("/anal/old")
def get_old_anal():

    conn = connect_to_mysql(host, user, password, db)

    full = {
        'data': [],
        'meta': {
            'timestamp': dt.now(ZoneInfo("Europe/Oslo"))
        }
        # 'db': [host, user, password, db, conn]
    }

    curr = conn.cursor()
    query = "SELECT ticker, type, created_at FROM crossovers ORDER BY created_at DESC"
    curr.execute(query)
    res = curr.fetchall()
    for r in res:
        if not r[1]:
            continue
        full['data'].append({'ticker': r[0], 'type': r[1], 'date': r[2]})
    # full['data'].append({'ticker':'EQNR', 'type':'gold100', 'date': '2025-04-08'})
    # full['data'].append({'ticker':'EQNR', 'type':'death200', 'date': '2025-04-08'})
    
    curr.close()
    conn.close()
    return full

@app.get("/anal/")
def get_anal():

    conn = connect_to_mysql(host, user, password, db)

    full = {
        'data': [],
        'meta': {
            'timestamp': dt.now(ZoneInfo("Europe/Oslo"))
        }
    }
    exchange = 'OL'
    curr = conn.cursor()

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
                    if after_close():
                        query = "INSERT INTO crossovers(ticker, type, created_at) VALUES(%s, %s, NOW())"
                        values = (ticker, ret['cross']['two'].lower() + '200' if ret['cross']['two'] else ret['cross']['one'].lower() + '100')
                        curr.execute(query, values)
                    

    conn.commit()
    curr.close()
    conn.close()
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
