from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer

# Read corpus file
with open('data/db.txt', 'r', encoding='utf-8') as f:
    corpus = f.readlines()

#Create ChatBot instance and train
my_bot = ChatBot(input('Please enter the ChatBot name:'))
trainer = ListTrainer(my_bot)
print('Start training!')
trainer.train(corpus)
print('Training completed!')
