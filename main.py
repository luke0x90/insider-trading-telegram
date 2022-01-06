import datetime
import os
import time
import csv
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import mplfinance as mpf
from pandas_datareader import data as pdr
from my_telegram import bot_token, bot_chatID
import telegram
import codecs
from PIL import Image


tickers = []
csvReader = csv.reader(codecs.open('t212_tickers.csv', 'rU', 'utf-16'), delimiter=";")
for row in csvReader:
    tickers.append(row[0])

bot = telegram.Bot(token=bot_token)
yf.pdr_override()

headers = {
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'referer': 'https://www.dataroma.com/m/ins/ins.php',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
}


def get_insider_report(data, range=3):
    url = 'http://openinsider.com/screener?s=' + data[
            "ticker"] + '&o=&pl=&ph=&ll=&lh=&fd=' + str(range) + '&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1'
    response = requests.get(
        url,
        headers=headers).text
    soup = BeautifulSoup(response, 'html.parser')
    transactions = []

    sum_table = soup.find('table', attrs={'class': 'tinytable'})
    insiders = sum_table.find_all("tr")[1:]
    for insider in insiders:
        row = insider.find_all("td")
        transaction = row[11].text.replace("$", '').replace(",", '')
        if transaction == '':
            transaction = 0
        when = row[1].text
        when = datetime.datetime.strptime(when, "%Y-%m-%d %H:%M:%S")
        howmuch = row[7].text
        transactions.append([int(transaction), when, float(howmuch.strip("$").replace(",",""))])
    data["transactions"] = transactions
    total = 0
    for i in transactions:
        total += i[0]
    data["overall"] = str(total)
    return data


def get_recent_insider_buys():
    response = requests.get(
        'http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=1&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=100&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&iscfo=1&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1',
        headers=headers)
    response = response.text
    soup = BeautifulSoup(response, 'html.parser')
    companies = []

    sum_table = soup.find('table', attrs={'class': 'tinytable'})
    if not sum_table:
        return companies
    insiders = sum_table.find_all("tr")[1:]
    for insider in insiders:
        data = {}
        row = insider.find_all("td")
        data["date"] = row[1].text
        data["ticker"] = row[3].text
        data["name"] = row[4].text
        data["insider_name"] = row[5].text
        data["title"] = row[6].text
        data["price"] = row[8].text
        data["quantity"] = row[9].text
        data["owned"] = row[10].text
        data["delta"] = row[11].text
        data["value"] = row[12].text
        data = get_insider_report(data, 90)
        if data["ticker"].strip() in tickers:
            companies.append(data)

    return companies


def get_formatted_message(data):
    e_char = "+.-()"
    msg = """* """ + data["ticker"] + " - " + data["name"] + """*\n
""" + data["insider_name"] + " bought " + data["quantity"].strip("+") + " @ " + data["price"] + " for a total of " + data["value"].strip("+") \
          + ". This increased their holdings by " + data["delta"] + """\n\nThe stock last closed at $""" + str(round(data["stock_price"],2)) + ". \n\nInsider trading on this stock totals " + "${:,.2f}".format(float(data["overall"])) + " for the last 3 months. \n\n" + "These are the recent insider transactions: \n"
    for i in data["transactions"]:
        msg += "* " + i[1].strftime("%d.%m.%y") + " * " + "${:,.2f}".format(i[0])  + " @ " + "${:,.2f}".format(i[2]) + "\n"
    for char in e_char:
        msg = msg.replace(char, '\\' + char)
    return msg


def generate_baseline():
    companies = get_recent_insider_buys()
    if not companies:
        bot.sendMessage(bot_chatID, "No insider trading found today :(")
        return
    for company in companies:
        ticker_price = pdr.get_data_yahoo(company["ticker"], datetime.date.today() - datetime.timedelta(days=365),
                                          datetime.date.today())
        company["stock_price"] = ticker_price.Close.array[-1]
        if not os.path.exists("charts"):
            os.makedirs("charts")
        filename = "charts" + os.path.sep + company["ticker"] + ".png"
        print("Notifying : " + company["ticker"])
        text = get_formatted_message(company)
        time.sleep(7.5)
        bot.sendMessage(bot_chatID, text, parse_mode="MarkdownV2")
        mpf.plot(ticker_price, style='yahoo', type='candle', savefig=filename)
        img = Image.open(filename)
        resized_img = img.resize((300, 158))
        resized_img.save(filename)
        bot.sendPhoto(bot_chatID, photo=open(filename, 'rb'))

def clear_chat():
    msg = bot.sendMessage(bot_chatID, "Starting Check...")
    start = 0
    id = msg["message_id"]
    while True:
        try:
            bot.deleteMessage(bot_chatID, id)
            start = 1
            id -= 1
        except:
            if start == 1:
                return


if __name__ == '__main__':
    clear_chat()
    generate_baseline()
