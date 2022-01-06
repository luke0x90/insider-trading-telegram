# Insider Trading Notifications

Sends telegram message notifying user of insider buying for T212 listed stocks within the last day. The trades are limited to CFO insider buys as this has historically been the strongest indicator of positive sentiment.

The signals should not be used as purchase indicators, but instead in conjunction with other sources.

`my_telegram.py`
```
bot_token = '1234'
bot_chatID = '1234'
```

