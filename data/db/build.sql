CREATE TABLE IF NOT EXISTS exp (
    UserID integer PRIMARY KEY,
    XP integer DEFAULT 0,
    XPSpent integer DEFAULT 0,
    Level integer DEFAULT 0,
    XPLock text DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS twitter (
    UserID integer PRIMARY KEY,
    TwitterName varchar UNIQUE DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS latest_tweet_id (
    TweetID integer PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS latest_tweet_likes (
    TwitterName varchar PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS latest_tweet_retweets (
    TwitterName varchar PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS followers (
    TwitterName varchar PRIMARY KEY
);