import sys
import csv
import ast
import pandas as pd
from itertools import islice
from scipy import spatial


def clean_records(topic_tuples):
    topic_records = []
    for topic in topic_tuples:
        tuple_count = len(topic.split(','))
        topic = topic.replace("[", "(")
        topic = topic.replace("]", ")")
        topic_new = ast.literal_eval(topic)
        print topic_new
        if tuple_count > 2:
            topic_record = dict((str(x), y) for x, y in topic_new)
            topic_records.append(topic_record)
        else:
            topic_record[str(topic_new[0])] = topic_new[1]
            print topic_record
            topic_records.append(topic_record)

    return topic_records


def read_mentor_profile(mentor_count):
    mentor_list = []
    with open("auth_list.csv") as mentorfile:
        reader = csv.reader(mentorfile)
        for row in islice(reader, mentor_count):
            mentor_list.append(row)

    return mentor_list


def main(no_mentors, user_record):
    mentors = read_mentor_profile(no_mentors)
    mentor_names = [mentor[0] for mentor in mentors]
    topic_tuples = [mentor[1] for mentor in mentors]

    topic_records = clean_records(topic_tuples)

    mentor_df = pd.DataFrame.from_records(topic_records)
    mentor_df.index = mentor_names
    mentor_df = mentor_df.fillna(0)

    user_df = pd.DataFrame.from_records(user_record)
    user = user_df.values.tolist()[0]

    # get cosine score between user and mentors
    css_list = get_css(mentor_df, user)
    css_df = pd.DataFrame(css_list, columns=['mentor', 'css'])
    recommended_mentors = css_df.query('css>0.5')['mentor']

    print recommended_mentors

def get_css(mentor_df, user):
    result_list = []
    for x, y in zip(mentor_df.values.tolist(), mentor_df.index):
        result = 1 - spatial.distance.cosine(user, x)
        result_list.append((y, result))
    return result_list


if __name__ == "__main__":
    num_mentors = sys.argv[1]
    user_preference_record = sys.argv[2]
    # e.g {'1':[1],'2':[1]} and so on till 20
    # user_preference_record = {'1': [0], '2': [1], '3': [1], '4': [1], '5': [0], '6': [0], '7': [0], '8': [0],
    #                '9': [0], '10': [0], '11': [0], '12': [0], '13': [0], '14': [0],
    #                '15': [0], '16': [0], '17': [0], '18': [0], '19': [0], '20': [0]}
    main(num_mentors,user_record=user_preference_record)