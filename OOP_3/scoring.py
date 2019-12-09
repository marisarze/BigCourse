import random
import logging

def get_score(store, phone=None, email=None, birthday=None, gender=None, first_name=None, last_name=None):
    score = 0
    if phone:
        logging.info('first plus')
        score += 1.5
    if email:
        logging.info('second plus')
        score += 1.5
    if birthday and gender:
        logging.info('third plus')
        score += 1.5
    if first_name and last_name:
        logging.info('fourth plus')
        score += 0.5
    return score


def get_interests(store, cid):
    interests = ["cars", "pets", "travel", "hi-tech", "sport", "music", "books", "tv", "cinema", "geek", "otus"]
    return random.sample(interests, 2)
