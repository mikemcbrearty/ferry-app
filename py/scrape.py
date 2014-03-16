#!/usr/bin/env python

import datetime
import os
import time

import bs4
import psycopg2
import requests

ENV_VARS = {
    "FERRY_DBNAME": "dbname",
    "FERRY_DBUSER": "user",
    "FERRY_DBPWD": "password",
}
DB_CREDS = " ".join(ENV_VARS[var]+"="+os.environ[var] for var in ENV_VARS.keys() if var in os.environ)

FERRIES = {
    "366952890": "Spirit of America",
    "366952870": "Sen. John J Marchi",
    "366952790": "Guy V Molinari",
    "367000140": "Samuel I Newhouse",
    "367000150": "Andrew J Barberi",
    "367000190": "John F Kennedy",
    "367000110": "John Noble",
    "367000120": "Alice Austen",
}

def get(mmsi):
    """ Returns html of a vessel information page
    for a given vessel identified by mmsi. """
    url = 'http://www.aishub.net/ais-hub-vessel-information.html'
    params = {'mmsi': mmsi}
    r = requests.get(url, params=params)
    return r.text


def html_to_dict(html):
    """ Returns dict of property-value pairs
    from vessel information page table. """
    soup = bs4.BeautifulSoup(html)
    if soup.table:
        trs = list(soup.table.find_all("tr"))[1:]
        pairs = [fmt([tag_to_string(td) for td in tr.children if type(td)==bs4.element.Tag]) for tr in trs]
        return dict(pairs)
    else:
        return {}


def tag_to_string(tag):
    """ Returns string contained by (possibly nested) bs4.element.Tag. """
    elem = tag.children.next()
    if type(elem) == bs4.element.Tag:
        return tag_to_string(elem)
    else:
        return elem


def fmt(pair):
    """ Coerce selected values from string to appropriate type. """
    action = {u'LATITUDE:': lambda v: float(v.replace(u' \xb0', u'')),
              u'LONGITUDE:': lambda v: float(v.replace(u' \xb0', u'')),
              u'MMSI': int,
              u'LAST UPDATE:': lambda v: datetime.datetime.strptime(v, '%d-%m-%Y %H:%M') + datetime.timedelta(hours=-2)}
    key, value = pair
    if key in action:
        return [key, action[key](value)]
    else:
        return pair


def latest_update(cur, mmsi):
    cur.execute('SELECT MAX(last_update) FROM locations WHERE mmsi=%s;', (mmsi,))
    return cur.fetchall()[0][0]


def push_to_db(d):
    conn = psycopg2.connect(DB_CREDS)
    cur = conn.cursor()
    cols = (u'MMSI', u'LATITUDE:', u'LONGITUDE:', u'LAST UPDATE:')
    vals = [d[c] for c in cols]
    if d[u'LAST UPDATE:'] != latest_update(cur, d[u'MMSI']):
        cur.execute('INSERT INTO locations VALUES (%s, %s, %s, %s);', vals)
        conn.commit()
    cur.close()
    conn.close()


def main():
    for mmsi in FERRIES.keys():
        html = get(mmsi)
        d = html_to_dict(html)
        if d: push_to_db(d)
        time.sleep(5)


if __name__ == '__main__':
    main()
