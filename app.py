import os
import pandas as pd
from flask import Flask, render_template, request
from sklearn.model_selection import train_test_split
import tweepy
from dotenv import load_dotenv
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

load_dotenv()

# Set up Tweepy API client
consumer_key = os.getenv('CONSUMER_KEY')
consumer_secret = os.getenv('CONSUMER_SECRET')
access_token = os.getenv('ACCESS_TOKEN')
access_secret = os.getenv('ACCESS_TOKEN_SECRET')

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_secret)
api = tweepy.API(auth)

# Load the CSV file into a DataFrame
df = pd.read_csv('models/hate_speech_model.csv')

# Split the data into feature and target variables
x = df['text']
y = df['is_toxic']

toxicity = 0

# convert the text data into numerical vectors using a CountVectorizer
vectorizer = CountVectorizer()
x = vectorizer.fit_transform(x)

# split the data into training and testing sets
x_train, x_test, y_train, y_test = train_test_split(
    x, y, test_size=0.2, random_state=42)

# train a logistic regression model on the training data
model = LogisticRegression()
model.fit(x_train, y_train)

# Get input parameters from request
app = Flask(__name__)

# Function to format number
def format_number(num):
    if num < 1000:
        return str(num)
    elif num >= 1000 and num < 1000000:
        return '{:.1f}K'.format(num / 1000)
    elif num >= 1000000 and num < 1000000000:
        return '{:.1f}M'.format(num / 1000000)
    else:
        return '{:.1f}B'.format(num / 1000000000)

# Function to check if a tweet contains hate speech
def is_toxic(text):
    vec = vectorizer.transform([text])
    percentage = round((model.predict_proba(vec)[0][1] * 100), 2)

    if percentage >= 65.00:
        return True
    else:
        return False

# Flask app setup
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/results', methods=['GET', 'POST'])
def results():
    if request.method == 'GET':
        return render_template('index.html')

    username = request.form['username']
    posts = int(request.form['posts'])

    # Get tweets from Twitter API
    tweets = []
    try:
        for tweet in tweepy.Cursor(api.user_timeline, screen_name=username, tweet_mode='extended').items(posts):
            tweets.append(tweet)
# Old version of tweepy: TweepError was replaced with TweepyException
    except tweepy.TweepyException:     
        error_message = 'An error occurred. Please try again later.'
        return render_template('index.html',error_message=error_message) 
    
# this used to render error.html, the file did not exist so I changed it to index.html with error message

    # Perform hate speech detection on the tweets
    labels = [is_toxic(tweet.full_text) for tweet in tweets]

    # Compute hate speech detection metrics
    num_hateful = sum(labels)
    num_total = len(tweets)
    hate_speech_ratio = num_hateful / num_total * 100

    # Compute the average toxicity percentage
    toxicity = sum([model.predict_proba(vectorizer.transform([tweet.full_text]))[0][1] for tweet in tweets]) / num_total

    # Get user's followers and following
    user = api.get_user(screen_name=username)
    followers_count = user.followers_count
    following_count = user.friends_count

    # Convert the counts to K, M, or B format
    followers_count = format_number(followers_count)
    following_count = format_number(following_count)

    # Render the results template
    return render_template('results.html', username=username, posts=posts, num_total=num_total, num_hateful=num_hateful, hate_speech_ratio=hate_speech_ratio, tweets=tweets, format_number=format_number, is_toxic=is_toxic, toxicity=toxicity, followers_count=followers_count, following_count=following_count)

if __name__ == '__main__':
    app.run(debug=True)
