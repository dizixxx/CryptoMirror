# *CryptoMirror*


**CryptoMirror** - это проект для симуляции торговли криптовалютами с использованием Binance API и создания Telegram-бота для взаимодействия с пользователями. Бот позволяет получать актуальные данные о криптовалютах и проводить торговые операции.

Проект использует библиотеки:
- `aiogram` для создания и работы с Telegram-ботом.
- `python-binance` для взаимодействия с Binance API.
- `requests` для HTTP-запросов.
- `python-dotenv` для безопасного хранения API ключей и других конфиденциальных данных.

## Алгоритм запуска

Для того чтобы запустить проект, следуйте этим шагам:

```bash
git clone https://github.com/dizixxx/CryptoMirror.git
cd CryptoMirror
pip install -r requirements.txt
# create .env file
python main.py
```

### **Project architecture**:
```
CryptoMirror/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── crud.py
│   │   ├── models.py
│   │   └── init_engine.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py
│   │   ├── prices.py
│   │   ├── buy.py
│   │   ├── sell.py
│   │   ├── balance.py
│   │   ├── portfolio.py
│   │   ├── help.py 
│   ├── services/
│   │   ├── __init__.py
│   │   ├── binance.py
│   │   ├── prices_uploader.py
│   └── utils/
│       ├── __init__.py
│   │   ├── keyboards.py
├── tools/
│   ├── ava_cryptomirror.jpg
├── .gitignore
├── trading.db
├── requirements.txt
└── README.md
```