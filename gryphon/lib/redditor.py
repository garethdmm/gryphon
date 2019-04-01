# -*- coding: utf-8 -*-
import json
import os

import praw
from gryphon.lib.session import get_a_redis_connection

# agent needs to be unique according to reddits api rules.
app_name = 'breaking_news_redditor_12809372502418712398'
story_list_key = 'news_already_seen'

def get_reddit_breaking_news(subreddit, upvote_threshold=500):
    try:
        r = praw.Reddit(user_agent=app_name)
        redis = get_a_redis_connection(creds=os.environ['NOODLE_DB_REDIS'])

        news_already_seen = json.loads(redis.get(story_list_key) or '[]')

        breaking_news = []

        submissions = r.get_subreddit(subreddit).get_hot(limit=100)

        for s in submissions:
            if s.score > upvote_threshold and s.url not in news_already_seen:
                news = {'title': s.title, 'url': s.url, 'comments_url': s.permalink}
                breaking_news.append(news)
                news_already_seen.append(s.url)

        redis.set(story_list_key, json.dumps(news_already_seen))
        return breaking_news
    finally:
        redis.connection_pool.disconnect()
