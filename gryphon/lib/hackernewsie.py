# -*- coding: utf-8 -*-
import json
import os

from gryphon.lib.session import get_a_redis_connection
from delorean import Delorean, epoch
import requests

#needs search query, start_time, end_time and score.
hn_url = "http://hn.algolia.com/api/v1/search_by_date?"\
            "query=%s&"\
            "tags=story&"\
            "hitsPerPage=500&"\
            "numericFilters=created_at_i>%s,points>=%s"

story_list_key = 'news_already_seen'


def get_hn_breaking_news(keywords={'bitcoin': 3, 'bitstamp': 0}):
    # keywords dictionary represents a search term paired with the threshold
    # for how many upvotes results for that term need to be considered breaking news
    try:
        redis = get_a_redis_connection(creds=os.environ['NOODLE_DB_REDIS'])

        news_already_seen = json.loads(redis.get(story_list_key) or '[]')
        breaking_news = []

        one_day_ago = Delorean().last_day(1).epoch

        for keyword, upvote_threshold in keywords.iteritems():
            # We quote the keywords so they don't match things that are close
            # Prompted by Bitcoin matching Ditchin (https://news.ycombinator.com/item?id=10850368)
            keyword = '"%s"' % keyword
            final_hn_url = hn_url % (keyword, one_day_ago, upvote_threshold)
            response = requests.get(final_hn_url).json()
            submissions = response['hits']

            for s in submissions:
                if s['url'] and s['url'] not in news_already_seen:
                    comments_url = 'https://news.ycombinator.com/item?id=%s' % s['objectID']
                    news = {'title': s['title'], 'url': s['url'], 'comments_url': comments_url}
                    breaking_news.append(news)
                    news_already_seen.append(s['url'])

        redis.set(story_list_key, json.dumps(news_already_seen))
        return breaking_news

    finally:
        redis.connection_pool.disconnect()
