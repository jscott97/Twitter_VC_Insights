import os
from unittest import result
from dotenv import load_dotenv
import tweepy
from tweepy import OAuthHandler, StreamingClient
from pprint import PrettyPrinter
import time
import json
from collections import Counter
from nltk.tokenize import TweetTokenizer
from nltk.corpus import stopwords
import matplotlib.pyplot as plt
import string
import sys

load_dotenv()
pp = PrettyPrinter(indent=4)

def tweepy_auth():
    API_KEY = os.getenv('API_KEY')
    API_KEY_SECRET = os.getenv('API_KEY_SECRET')
    ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
    ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')

    auth = OAuthHandler(API_KEY, API_KEY_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    return auth

def get_tweepy_client():
    auth = tweepy_auth()
    client = tweepy.API(auth)
    return client

def process_tweet(text, tokenizer=TweetTokenizer(), stopwords=[]):
    text = text.lower()
    tokens = tokenizer.tokenize(text)
    return [tok for tok in tokens if tok not in stopwords and not tok.isdigit() and 'http' not in tok]

def streaming_listener_json(query:list, delete_rules_after_stream=False):
    twitter_stream = CustomListener("Tweets", os.getenv('BEARER_TOKEN'))
    for rule in query:
        twitter_stream.add_rules(tweepy.StreamRule(rule))

    twitter_stream.filter(tweet_fields=['referenced_tweets'])
    
    if delete_rules_after_stream:
        for rule in twitter_stream.get_rules().data:
            twitter_stream.delete_rules([rule.id])

class CustomListener(StreamingClient):
    def __init__(self, file_name, bearer_token):
        super().__init__(bearer_token)
        self.file_name = file_name
        self.op_file = f"Stream_{self.file_name}.json"
        self.tweet_count = 0

    def on_connect(self):
        print("Connected")

    def on_data(self, data):
        try:
            with open(self.op_file, 'a') as f:
                if 'referenced_tweets' not in json.loads(data)['data']:
                    f.write(json.dumps(json.loads(data), indent=4))
                    f.write(',')
                    print(json.loads(data))
                    if self.tweet_count >= 5000:
                        self.disconnect()
                    self.tweet_count += 1
                    print(self.tweet_count)
                    return True
        except BaseException as e:
            print(f"Error reading data: {e}")


if __name__ == '__main__':
    query = ['Trump']

    # stream = streaming_listener_json(query, True)
    twitter_stream = CustomListener("Tweets", os.getenv('BEARER_TOKEN'))

    api = get_tweepy_client()

    with open('Found_Tweets.json', 'w') as f:  
        tweets = [tweet for tweet in tweepy.Cursor(api.search_tweets, q="Ukraine", lang='en', result_type="mixed", count=500).items()]
        for t in tweets:
            f.write(json.dumps(t._json, indent=4))
            f.write(',')

    fname = 'Stream_Tweets.json'
    tweet_tokenizer = TweetTokenizer()
    punct = list(string.punctuation)
    stopword_list = stopwords.words('english') + punct + ['rt', 'via', '...', '’', '“', '‘', 'like']

    tf = Counter()
    with open(fname, 'r') as f:
        data = json.load(f)

    for line in data:
        tweet = line['data']['text']
        tokens = process_tweet(tweet, tweet_tokenizer, stopword_list)
        tf.update(tokens)

    for tag, count in tf.most_common(20):
        print(f"{tag}: {count}")

    y = [count for tag, count in tf.most_common(20)]
    x = range(1, len(y) + 1)

    plt.bar(x, y)
    plt.title("Term frequencies used in Ukraine Stream Data")
    plt.ylabel("Frequency")
    plt.savefig('ukraine-term-distn.png')

