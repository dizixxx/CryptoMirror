# *CryptoMirror*

Project architecture:
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
│   │   ├── handlers.py 
│   ├── services/
│   │   ├── __init__.py
│   │   ├── binance.py
│   └── utils/
│       ├── __init__.py
│   │   ├── keyboards.py
├── tools/
│   ├── ava_cryptomirror.jpg
├── .gitignore
└── README.md
```