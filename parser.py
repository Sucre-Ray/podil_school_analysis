import json
import re
import os
import pandas as pd

import requests
import concurrent.futures
import osr
import geopandas

from bs4 import BeautifulSoup
from osgeo import ogr
from math import cos, inf
from shapely.geometry import Point


def load_input(path='podil school/Sheet2.html'):
    here = os.path.abspath(os.path.dirname(__file__))
    ppath = os.path.split(path)
    local_input = os.path.join(here, *ppath)
    if os.path.isfile(local_input):
        return read_input(local_input)


def read_input(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    return text


def combine_search_text(row):
    return '+'.join([row['city'], row['street'], row['bld_number']])


def calculate_distance(row):
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(4326)  # WGS 84
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(3857)  # Spherical mercator
    coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint(row['house_longitude'], row['house_latitude'])
    point2.AddPoint(row['school_longitude'], row['school_latitude'])
    point1.Transform(coordTransform)
    point2.Transform(coordTransform)
    factor = cos((row['house_latitude'] + row['school_latitude']) / 2)
    return round(point2.Distance(point1) / factor)


def prepare_url(adress):
    url = 'https://geocoder.api.here.com/6.2/' \
          'geocode.json?app_id={APP_ID}&' \
          'app_code={APP_CODE}&searchtext={adress}'
    return url.format(
        APP_ID=os.environ.get('HERE_MAPS_APP_ID'),
        APP_CODE=os.environ.get('HERE_MAPS_APP_CODE'),
        adress=adress
    )


def parse_school_info(url):
    r = requests.get(url)
    if r.status_code != 200:
        # don't handling exceptions as for test script
        return
    soup = BeautifulSoup(r.text, features="html.parser")
    rows = soup. \
        find('div', attrs={'id': 'organizationsList'}). \
        find_all('div', attrs={'class': 'row'})
    schools = [[row.
                    find('div', attrs={'class': 'span6'}).
                    find('h3').contents[0],

                row.find('div', attrs={'class': 'span6'}).
                    find('address').find('nobr').text
                ] for row in rows]
    return schools


def extract_school_id(c):
    pattern = re.compile(r'№\s*(\d+)')
    match = re.search(pattern, c)
    if match:
        return match.group(1)


def main():
    APP_ID = os.environ.get('HERE_MAPS_APP_ID')
    APP_CODE = os.environ.get('HERE_MAPS_APP_CODE')
    MAX_WORKERS = 20
    if not APP_ID or not APP_CODE:
        raise Exception('Please set up API keys for HERE MAPS')
    text = load_input()
    soup = BeautifulSoup(text, features="html.parser")

    data = []
    table = soup.find('table', attrs={'class': 'waffle'})
    table_body = table.find('tbody')

    rows = table_body.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        data.append(cols)
    SCHOOLS_URL = 'http://ua.kiev.parentsportal.com.ua/schools/?rayon=146'
    HEADERS = ['school', 'street', 'bld_number', 'whole_street_indicator']
    SCHOOL_HEADER = ['school_name', 'adress']
    CITY = 'Київ'
    df = pd.DataFrame(data=data, columns=HEADERS)
    df['city'] = [CITY] * len(df)
    house_data = df[df['bld_number'] != ''].reset_index(level=0, drop=True)

    house_data['search_text'] = house_data.apply(combine_search_text, axis=1)
    # I decided to exclude averaged data from experiment
    avg_street_data = df[df['bld_number'] == ''].reset_index(level=0, drop=True)
    school_data = pd.DataFrame(data=parse_school_info(SCHOOLS_URL),
                               columns=SCHOOL_HEADER)
    house_data['school_id'] = house_data['school'].apply(extract_school_id)
    school_data['school_id'] = school_data['school_name'].apply(extract_school_id)
    # refactor these 2 functions
    def update_location_house(url, ind):
        r = requests.get(url)
        if r.status_code != 200:
            # don't handling exceptions as for test script
            return
        d = json.loads(r.text)
        try:
            location = d['Response']['View'][0]['Result'][0]['Location']['DisplayPosition']
            house_data.loc[ind, 'house_latitude'] = location['Latitude']
            house_data.loc[ind, 'house_longitude'] = location['Longitude']
        except IndexError:
            print(url, d['Response'])

    def update_location_school(url, ind):
        r = requests.get(url)
        if r.status_code != 200:
            # don't handling exceptions as for test script
            return
        d = json.loads(r.text)
        try:
            location = d['Response']['View'][0]['Result'][0]['Location']['DisplayPosition']
            school_data.loc[ind, 'school_latitude'] = location['Latitude']
            school_data.loc[ind, 'school_longitude'] = location['Longitude']
        except IndexError:
            print(url, d['Response'])

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for index, row in house_data.iterrows():
            url = prepare_url(row['search_text'])
            executor.submit(update_location_house(url, index))

        for index, row in school_data.iterrows():
            url = prepare_url(CITY + '+' + row['adress'])
            executor.submit(update_location_school(url, index))
    # for test script just filter out adress that we cant find on maps
    house_data = house_data[house_data['house_longitude'].notnull()]
    school_data = school_data[school_data['school_longitude'].notnull()]
    data = pd.merge(house_data, school_data, left_on='school_id', right_on='school_id')
    data['distance_m'] = data.apply(calculate_distance, axis=1)
    data['geometry'] = data.apply(lambda x: Point((float(x['house_longitude']),
                                                   float(x['house_latitude']))),
                                  axis=1)
    data = geopandas.GeoDataFrame(data, geometry='geometry')
    data.to_file(os.path.join('data', 'MyGeometries.shp'),
                 driver='ESRI Shapefile')
    bins = [0, 500, 800, 1000, inf]
    labels = ['less 500', '500-800', '800-1000', 'greater 1000']
    # as I understood we need not intercepting intervals
    data['distance_bucket'] = pd.cut(data['distance_m'], bins, labels=labels)
    print((data.groupby(['distance_bucket']).size()).apply(lambda x: x / len(data)))
    print('home to school median distance: {}'.format(data['distance_m'].median()))


if __name__ == '__main__':
    main()
