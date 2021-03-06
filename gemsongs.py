from bs4 import BeautifulSoup
import requests
import json
import sqlite3
import plotly.graph_objs as go
from flask import Flask, render_template, url_for, request

CACHE_FILENAME = 'cache.json'
CACHE_DICT = {}
BASEURL = 'https://geology.com/gemstones/'
BASEURL2 = "https://itunes.apple.com/search"
KEYWORD = ""
GEM_KEYS = ["Chemical Classification","Color", "Streak", "Luster", \
           "Diaphaneity", "Cleavage", "Mohs Hardness", "Specific Gravity", \
           "Diagnostic Properties", "Chemical Composition", "Crystal System", \
           "Uses", "Name"]


#Part 1: Cache functions
def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.
    if the cache file doesn't exist, creates a new cache dictionary
    Parameters
    ----------
    None
    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict


def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close()


def make_url_request_using_cache(url, cache):
	'''Check the cache for a saved result for this url:values
    combo. If the result is found, return it. Otherwise send a new
    request, save it, then return it.
    Parameters
    ----------
    baseurl: string
        The URL for the nps webisite
    params: dict
        A dictionary of url:value pairs
    Returns
    -------
    dict
        the results of the query as a dictionary loaded from cache
        JSON'''
	if url in cache.keys():
		return cache[url]
	else:
		response = requests.get(url)
		cache[url] = response.text
		save_cache(cache)
		return cache[url]


def make_api_request_using_cache(url, params, cache):
	'''Check the cache for a saved result for this url+params:values
    combo. If the result is found, return it. Otherwise send a new
    request, save it, then return it.
    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    params: dict
        A dictionary of param:value pairs
    Returns
    -------
    dict
        the results of the query as a dictionary loaded from cache
        JSON
    '''
	if url+str(params) in cache.keys():
		return cache[url+str(params)]
	else:
		response = requests.get(url, params).json()
		cache[url+str(params)] = response
		save_cache(cache)
		return cache[url+str(params)]


#Part 2: Retrieve gemstones information functions
def build_gem_dict():
    ''' build a dictionary with key-value pairs: all the available
    gemstone name and its url
    Parameters
    ----------
    None
    Returns
    -------
    dict
    '''
    gem_url_dict = {}
    responsetext = requests.get(BASEURL)
    soup = BeautifulSoup(responsetext.text,'html.parser')
    searching_tb = soup.find('div', class_= 'right')
    gems = searching_tb.find_all('a')
    for gem in gems:
        gem_name = gem.get_text()
        gem_url = gem.get('href')
        gem_url_dict[gem_name.lower()] = gem_url
    return gem_url_dict


def get_gem_instance(url):
    ''' build an individual dictionary with key-value pairs of the Properties
    scraped from the url.
    Parameters
    ----------
    string
    Returns
    -------
    dict'''
    indi_gem_dict = {}
    responsetext = make_url_request_using_cache(url, CACHE_DICT)
    soup = BeautifulSoup(responsetext,'html.parser')
    try:
        searching_tb = soup.find('table', class_= 'ref', bgcolor="#ddd")
        if searching_tb == None:
            try:
                searching_tb = soup.find('table', class_= 'ref', bgcolor="#DDD")
            except:
                print('no properties')
        rows = searching_tb.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) > 1:
                title = tds[0].get_text()
                result = tds[1].get_text()
                indi_gem_dict[title] = result
        return indi_gem_dict
    except:
        pass


def get_all_gem_info(dict):
    ''' crawling every url in all gem dict and return a nested dictionaty
    of all the available gemstones properties.
    Parameters
    ----------
    dict
    Returns
    -------
    dict'''
    all_gem_dict = {}
    for k, v in gem_dict.items():
        all_gem_dict[k] = get_gem_instance(v)
    return all_gem_dict


def write_to_list(dict):
    ''' helper function to write the nested dictionaty into a list
    Parameters
    ----------
    dict
    Returns
    -------
    list'''
    all_gem_list = []
    for k, v in dict.items():
        if v is not None:
            all_gem_list.append(v)
            #v['Mohs Hardness'] = v['Mohs Hardness'].split()[0]
            v['Name'] = k
        else:
            pass
    return all_gem_list


#Part3: iTunes API functions
def search_itunesapi(url = BASEURL2, params= {"term" : KEYWORD, "limit" : 10}):
    '''Issues an HTTP GET request to return a representation of a resource.
    If no category is provided, the root resource will be returned.
    An optional query string of key:value pairs may be provided as
    search terms. If a match is achieved the JSON object that is returned
    will include a list property named 'results' that contains
    the resource(s) matched by the search query.

    Parameters
    ----------
    url (str): a url that specifies the resource, defaul Itunes.
    params (dict): optional dictionary of querystring arguments.

    Returns
    -------
    List
        decoded JSON document, a list of dict.
    '''
    response = requests.get(url, params).json()["results"]
    return response


def get_songlst(response):
    '''Parses the returned object of search_itunesapi and categorizes
    into three lists: song, movie and media. Return a dictionary that has
    3 key-value pairs, each value equals to the categorized lists.

    Parameters
    ----------
    List
        returned JSON objects
    Returns
    -------
    list
    '''
    song_lst = []
    for data in response:
        if 'kind' in data:
            if data['kind'] == 'song':
                song_lst.append(data)
        else:
            pass
    return song_lst


def clean_songlst(song):
    ''' helper function to write the list into a dictionary
    Parameters
    ----------
    list
    Returns
    -------
    dict'''
    dict = {}
    dict['SongName'] = song['trackName']
    dict['Artist'] = song['artistName']
    dict['Year'] = song["releaseDate"].split("-")[0]
    dict['Genre'] = song['primaryGenreName']
    return dict


def get_all_songs(all_gem_list):
    ''' helper function to write the nested dictionaty into a list
    Parameters
    ----------
    dict
    Returns
    -------
    list'''
    all_song_lst = []
    for gem in all_gem_list:
        keyword = gem['Name']
        try:
            result = search_itunesapi(url = BASEURL2, params= {"term" : keyword, "limit" : 10})
            if result != None:
                oldlst = get_songlst(result)
                for song in oldlst:
                    song = clean_songlst(song)
                    song['GemName'] = keyword
                    all_song_lst.append(song)
            else:
                pass
        except:
            pass
    return all_song_lst


#Part4: Database functions
def create_db():
    conn = sqlite3.connect('gemstones.sqlite')
    cur = conn.cursor()

    drop_gems_sql = 'DROP TABLE IF EXISTS "Gems"'
    drop_songs_sql = 'DROP TABLE IF EXISTS "Songs"'

    create_gems_sql = '''
        CREATE TABLE IF NOT EXISTS "Gems" (
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "Classification" TEXT NOT NULL,
            "Color" TEXT NOT NULL,
            "Streak" TEXT NOT NULL,
            "Luster" TEXT NOT NULL,
            "Diaphaneity" TEXT NOT NULL,
            "Cleavage" TEXT NOT NULL,
            "Mohs" REAL,
            "Gravity" TEXT NOT NULL,
            "Properties" TEXT NOT NULL,
            "Composition" TEXT NOT NULL,
            "Crystal" TEXT NOT NULL,
            "Uses" TEXT NOT NULL,
            "Name" TEXT NOT NULL
        )
    '''
    create_songs_sql = '''
        CREATE TABLE IF NOT EXISTS "Songs" (
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "SongName" TEXT NOT NULL,
            "Artist" TEXT NOT NULL,
            "Year" INTEGER NOT NULL,
            "Genre" TEXT NOT NULL,
            "GemName" TEXT NOT NULL,
            "GemId" INTEGER
        )
    '''

    cur.execute(drop_gems_sql)
    cur.execute(drop_songs_sql)
    cur.execute(create_gems_sql)
    cur.execute(create_songs_sql)
    conn.commit()
    conn.close()


def load_gems():
    insert_gem_sql ='''
        INSERT INTO Gems
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    conn = sqlite3.connect('gemstones.sqlite')
    cur = conn.cursor()
    for i in all_gem_lst:
        try:
            cur.execute(insert_gem_sql,
                [
                    i["Chemical Classification"],
                    i["Color"],
                    i["Streak"],
                    i["Luster"],
                    i["Diaphaneity"],
                    i["Cleavage"],
                    float(i["Mohs Hardness"].split()[0]),
                    i["Specific Gravity"],
                    i["Diagnostic Properties"],
                    i["Chemical Composition"],
                    i["Crystal System"],
                    i["Uses"],
                    i["Name"]
                ]
            )
        except:
            pass
    conn.commit()
    conn.close()


def load_songs():
    select_gem_id_sql = '''
        SELECT Id FROM Gems
        WHERE Name = ?
    '''

    insert_song_sql = '''
        INSERT INTO Songs
        VALUES (NULL, ?, ?, ?, ?, ?, ?)
    '''
    conn = sqlite3.connect('gemstones.sqlite')
    cur = conn.cursor()

    for i in all_song_lst:
        cur.execute(select_gem_id_sql, [i['GemName']])
        res = cur.fetchone()
        GemId = None
        if res is not None:
            GemId = res[0]

        cur.execute(insert_song_sql,
            [
                i["SongName"],
                i["Artist"],
                i["Year"],
                i["Genre"],
                i['GemName'],
                GemId
            ]
        )
    conn.commit()
    conn.close()


def connection(command):
    '''Added function to constructs and executes SQL query
    to retrieve data based on query (reduce repetitive code)

    Parameters
    ----------
    quert:string

    Returns
    -------
    list
        a list of tuples that represent the query result
    '''
    connection = sqlite3.connect('gemstones.sqlite')
    cursor = connection.cursor()
    result = cursor.execute(command).fetchall()
    connection.close()
    return result


def get_gem_data(gemname):
    '''return the properties of the inputed gem databa
    '''
    command = f'''SELECT Classification, Color, Streak, Luster, Diaphaneity,\
               Cleavage, Mohs, Gravity, Properties, Composition, Crystal,\
               Uses
               FROM Gems AS b
               WHERE Name = "{gemname}"
                '''
    lst = connection(command)
    merged_list = tuple(zip(GEM_KEYS, lst[0]))
    return merged_list


def get_soft_gem():
    command = f'''SELECT Name, Mohs
               FROM Gems AS b
               ORDER BY Mohs ASC
               LIMIT 15
                '''
    return connection(command)


def get_hard_gem():
    command = f'''SELECT Name, Mohs
               FROM Gems AS b
               ORDER BY Mohs DESC
               LIMIT 15
                '''
    return connection(command)


def get_songs(gemname):
    command = f'''SELECT SongName, Artist, Year, Genre
               FROM Songs AS s
                JOIN Gems AS g
                ON s.GemId = g.Id
               WHERE GemName = "{gemname}"
               ORDER BY Mohs DESC
               LIMIT 15
                '''
    return connection(command)


#Flask app + Plotly
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/visit/')
def visit():
    return render_template('visit.html')


@app.route('/compare/')
def compare():
    return render_template('compare.html')


@app.route('/mohs',methods=['POST'])
def mohs():
    mohs_choice = request.form['mohs']
    if mohs_choice == 'soft':
        soft_gem_lst = get_soft_gem()
        xvals = [gem[0] for gem in soft_gem_lst]
        yvals = [gem[1] for gem in soft_gem_lst]

        fig = go.Figure(go.Bar(x=xvals,
                          y=yvals,
                          width=0.5))
        fig.update_traces(marker_color=["#ff9900","#ca431d","#ca431d",\
                         "#ca431d","#8b104e","#8b104e","#8b104e","#8b104e",\
                         "#520556","#520556","#520556","#520556","#520556",\
                         "#330336","#330336"])
        fig.update_yaxes(range=[0, 10])
        fig.update_layout(title="Top 15 Softest Gemstones")
        div = fig.to_html(full_html=False)
        #soft polar
        fig2 = go.Figure(go.Barpolar(
            r=[gem[1] for gem in soft_gem_lst],
            text=[gem[0] for gem in soft_gem_lst],
            #theta=[65, 15, 210, 110, 312.5, 180, 270],
            width=[10,10,10,10,10,10,10,10,10,10,10,10,10,10,10],
            ids=[gem[0] for gem in soft_gem_lst],
            marker_color=["#ff9900","#ca431d","#ca431d","#ca431d","#8b104e",\
                          "#8b104e","#8b104e","#8b104e","#520556","#520556",\
                          "#520556","#520556","#520556","#330336","#330336"],
            #marker_line_color="#30475e",
            #marker_line_width=2,
            opacity=0.95
        ))
        fig2.update_layout(
            template=None,
            title='Top 15 Softest Gemstones',
            font_size=16,
            polar = dict(
                radialaxis = dict(range=[0, 10], showticklabels=False, ticks=''),
                #angularaxis = dict(showticklabels=False, ticks=''),
            )
        )
        div2 = fig2.to_html(full_html=False)
        return render_template("mohs.html", plot_div1=div, plot_div2=div2)
    if mohs_choice == 'hard':
        hard_gem_lst = get_hard_gem()
        xvals = [gem[0] for gem in hard_gem_lst]
        yvals = [gem[1] for gem in hard_gem_lst]

        fig = go.Figure(go.Bar(x=xvals,
                          y=yvals,
                          width=0.5))
        fig.update_traces(marker_color=["#f67280","#c06c84","#c06c84",\
                          "#c06c84","#6c5b7b","#6c5b7b","#6c5b7b","#6c5b7b",\
                          "#6c5b7b","#355c7d","#355c7d","#355c7d","#213a4f",\
                          "#213a4f","#213a4f","#213a4f"])
        fig.update_layout(title="Top 15 Hardest Gemstones")
        div = fig.to_html(full_html=False)

        fig2 = go.Figure(go.Barpolar(
            r=[gem[1] for gem in hard_gem_lst],
            text=[gem[0] for gem in hard_gem_lst],
            #theta=[65, 15, 210, 110, 312.5, 180, 270],
            width=[10,10,10,10,10,10,10,10,10,10,10,10,10,10,10],
            ids=[gem[0] for gem in hard_gem_lst],
            marker_color=["#f67280","#c06c84","#c06c84","#c06c84","#6c5b7b",\
                           "#6c5b7b","#6c5b7b","#6c5b7b","#6c5b7b","#6c5b7b",\
                           "#355c7d","#355c7d","#355c7d","#213a4f","#213a4f","#213a4f"],
            #marker_line_color="#30475e",
            #marker_line_width=2,
            opacity=0.95
        ))
        fig2.update_layout(
            template=None,
            title='Top 15 Hardest Gemstones',
            font_size=16,
            polar = dict(
                radialaxis = dict(range=[0, 10], showticklabels=False, ticks=''),
                #angularaxis = dict(showticklabels=False, ticks=''),
            )
        )
        div2 = fig2.to_html(full_html=False)
        return render_template("mohs.html", plot_div1=div, plot_div2=div2)
    else:
        command = f'''SELECT Name, Mohs
                   FROM Gems AS b
                   ORDER BY Mohs ASC
                    '''
        mohs_lst = connection(command)
        fig = go.Figure(data=go.Scatter(
        x=[gem[0] for gem in mohs_lst],
        y=[gem[1] for gem in mohs_lst],
        mode='markers',
        marker=dict(size=[gem[1]*10 for gem in mohs_lst],
                    color=[gem[1] for gem in mohs_lst])
                    ))
        div = fig.to_html(full_html=False)
        div2 = 'Comparison of the Mohs Hardness of All Gemstones'
        return render_template("mohs.html", plot_div1=div, plot_div2=div2)


@app.route('/gems', methods=['GET','POST'])
def gems():
    gem = request.form['gem']
    properties = get_gem_data(gem)
    songs = get_songs(gem)
    return render_template('gems.html', gem=gem, properties = properties, songs=songs)


#Main
if __name__ == "__main__":
    CACHE_DICT = open_cache()
    gem_dict = build_gem_dict()
    #get_gem_instance("https://geology.com/gemstones/red-beryl/")
    #print(get_all_gem_info(gem_dict))
    all_gem_dict = get_all_gem_info(gem_dict)
    all_gem_lst = write_to_list(all_gem_dict)
    #print(len(all_gem_lst))
    all_song_lst = get_all_songs(all_gem_lst)
    create_db()
    load_gems()
    load_songs()
    #print(get_songs('opal'))
    #print(get_soft_gem())
    #print(get_hard_gem())
    #graph_hardbar()
    #graph_hardpolar()
    #graph_softbar()
    #graph_softpolar()
    #gragh_bubble()
    #print(get_gem_data('amazonite'))
    app.run(debug=True)
