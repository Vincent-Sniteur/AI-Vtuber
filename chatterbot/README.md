## Running environment
-Python 3.6+

## Install dependencies
Install the required libraries using the following command on the command line:
```bash
pip install spacy ChatterBot
```

If an error occurs during ChatterBot installation, please go to https://github.com/RaSan147/ChatterBot_update to install the new version. Download it and enter `python setup.py install`
The installation is slow, you can disassemble it to install `pip install SQLAlchemy==1.3.24`

## How to train your own AI?
- Open `data/db.txt` and write the content you want to train in the following format
```
ask
answer
ask
answer
```
- Rename the file to `data/db.txt`
- Start the program by running the following command from the command line:
```bash
pythontrain.py
```
- The trained model is called `db.sqlite3` and can be used by double-clicking `main.py`

## common problem
1. It prompts that en-core-web-sm is missing, open the terminal and enter
```bash
python -m spacy download en_core_web_sm
```
2. Error: no module named ‘spacy’ solution
```bash
pip install spacy
```

## License
MIT license. Please see the LICENSE file for details.

## Replenish

### ChatterBot
ChatterBot is an open source Python chatbot framework that uses machine learning algorithms (especially natural language processing, text semantic analysis, etc.) to implement automatic chat systems based on rules and context. It allows developers to build various types of chat robots through simple configuration and training, including question and answer robots, task-based robots, chat robots, etc.

The core idea of ChatterBot is to use machine learning and natural language processing technology to analyze and predict user input based on historical conversation data, and then generate responses. Based on this method, the chatbot's response will be more intelligent, flexible, and close to human conversation. In addition, ChatterBot supports multiple storage methods, such as JSON, SQLAlchemy, MongoDB, etc., as well as multiple interface calling methods, such as RESTful API, WebSocket, etc., making it easy for developers to integrate in different scenarios.

Overall, ChatterBot is a very powerful, flexible, and easy-to-use chatbot framework that helps developers quickly build personalized and customized chatbots to improve user experience and service quality.