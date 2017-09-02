import psycopg2
import nltk
import pandas as pd
import langid
import stop_words
import string
import re
import csv
from gensim import corpora, models

DATABASE_NAME = "dblp"


def open_db_conn(db_name):
    conn_string = "host='localhost' dbname=%s user='postgres'" % db_name
    print "Connecting to database\n	->%s" % conn_string

    # get a connection, if a connect cannot be made an exception will be raised here
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()

    return conn, cursor


def close_db_conn(con):
    con.close()


def query(tbl_query,cursor):
    cursor.execute(tbl_query)
    results = cursor.fetchall()

    return results


def transform_text(raw_text, tokenizer, total_stop_w):
    tokens = tokenizer.tokenize(raw_text.lower())

    # remove non utf-8 words
    utf8_tokens = [t.decode('utf-8', 'ignore').encode("utf-8") for t in tokens if
                   t.decode('utf-8', 'ignore').encode("utf-8") != ""]
    # remove punctuations
    punc_tokens = [s.translate(None, string.punctuation) for s in utf8_tokens if
                   s.translate(None, string.punctuation) != ""]
    # remove words with only digits
    alpha_tokens = [re.sub(r'[0-9]', "", t) for t in punc_tokens]
    # remove single character instances
    singlechar_tokens = [w for w in alpha_tokens if len(w) > 1]
    # remove stop words including english, tech words and months
    stopped_tokens = [t for t in singlechar_tokens if t not in total_stop_w]
    # remove any empty instances
    clean_tokens = [p for p in stopped_tokens if p != ""]

    return clean_tokens


def extract_topic(title_texts):
    dictionary = corpora.Dictionary(title_texts)
    # convert to bag-of-words
    corpus = [dictionary.doc2bow(text) for text in title_texts]
    # This list of tuples represents (term ID, term frequency) pairs.
    lda_multicore = models.ldamulticore.LdaMulticore(corpus, num_topics=20, id2word=dictionary, passes=5)
    lda_multicore.save("lda_auth_20")

    return lda_multicore, corpus

def main():
    auth_pubs_q = 'select * from Author_Extra'
    conn, cursor = open_db_conn('dblp')
    # cursor.execute(pub_title_q)
    # titles = cursor.fetchall()

    dblp_data = query(auth_pubs_q, cursor)
    df_dblp_data = pd.DataFrame(dblp_data, columns=['auth_id', 'auth_name', 'pub_id', 'pub_title', 'pub_auth_count'])

    df_dblp_grouped = df_dblp_data.groupby('auth_name')['pub_title'].apply(list).reset_index()

    # Use Langid library to detect the language of the publication titles
    df_dblp_grouped['lang'] = df_dblp_grouped['pub_title'].apply(lambda val: langid.classify(str(val)))
    df_dblp_grouped['lang_code'] = pd.DataFrame(df_dblp_grouped['lang'].tolist())[0]

    # For simplification purposes, we use only English titles in our system
    # Total pub titles ~3.7mil, english pub titles ~3.5mil and when concatenated per
    # author ~2mil and only english ~1.9mil
    df_dblp_en = df_dblp_grouped.query('lang_code=="en"')
    raw_titles = df_dblp_en['pub_title']

    # create English stop words list
    en_stop_w = stop_words.get_stop_words('en')
    tech_stop_w = ['symposium', 'proceedings', 'workshop', 'journal', 'ieee', 'international', 'conference', 'bsn',
                   'th', 'st', 'rd', 'ft','based','using','problem','problems']
    month_stop_w = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
                    'november', 'december']
    total_stop_w = en_stop_w + tech_stop_w + month_stop_w
    tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')

    title_texts = []
    for raw_list in raw_titles:
        raw = ' '.join(str(v) for v in raw_list)
        clean_tokens = transform_text(raw, tokenizer, total_stop_w)
        title_texts.append(clean_tokens)

    lda_model, lda_corpus = extract_topic(title_texts)

    # Save topics with term probs in a csv for later inspection
    topics = lda_model.show_topics(formatted=True, num_topics=20, num_words=20)
    with open('topics_list.csv', 'wb') as topicfile:
        wr = csv.writer(topicfile, quoting=csv.QUOTE_ALL)
        for topic in topics:
            wr.writerow(topic)
            wr.writerow("\n\n")

    # Save Document topics probs in a csv to be loaded in the database.
    with open('auth_list.csv', 'wb') as authfile:
        wr = csv.writer(authfile, quoting=csv.QUOTE_ALL)
        for i, j in zip(lda_corpus, df_dblp_en.index):
            wr.writerow((df_dblp_en['auth_name'][j], i))

    close_db_conn(conn)


if __name__ == "__main__":
    main()

