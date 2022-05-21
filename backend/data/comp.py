from backend.resources.database import DBClient
from flask import request
from nitrotype import Racer
import jsonpickle, random
import cloudscraper, json, time, copy
dbclient = DBClient() 
def get_comp_data(compid):
    #get collection first
    collection = dbclient.db.test # collection in the comps database named test for some reason lol
    #now to get the data
    data = dbclient.get_array(collection, {'compid': compid})
    #now that we got the data let's parse the data and change it into leaderboards
    return data, dbclient
def team_data(team):
    team = team.upper()
    scraper = Racer('travis').requests
    return scraper.get(f'https://www.nitrotype.com/api/v2/teams/{team}').text
def leaderboards(compid, category="races"):
    data, dbclient = get_comp_data(compid)
    print(compid)
    newdata = update_comp(data, dbclient)
    print(data == newdata)
    data = newdata
    usernames = []
    displays = []
    categorylist = []
    datalist = []
    for user in data['players']:
        if user['stillinteam'] == False:
          continue
        #print(user)
        user['wpm'] = round(float(user['wpm']),2)
        user['accuracy'] = round(float(user['accuracy']),2)
        user['points'] = round(float(user['points']),2)
        usernames.append(user['username'].lower())
        displays.append(user['display'])
        if category == "races":
            categorylist.append(user['total-races'])
        elif category == "points":
            categorylist.append(user['points'])
        elif category == "speed":
            categorylist.append(user['wpm'])
        elif category == "accuracy":
            categorylist.append(user['accuracy'])
        user['points'] = user['total-races']*(100+float(user['wpm'])/2)*user['accuracy']/100
        try:
            user['points'] = user['total-races']*(100+float(user['wpm'])/2)*user['accuracy']/100
            userpoints = user['points']
            user['points'] = round(float(userpoints))
            user['points'] = "{:,}".format(user['points'])
        except:
            user['total-races'] = 0
            user['points'] = 0
            user['wpm'] = 0
            user['accuracy'] = 0
        datalist.append((user['total-races'], user['points'], user['wpm'], user['accuracy']))
    sortcategory = sorted(categorylist, reverse=True)
    zipped_lists = zip(categorylist, usernames, displays, datalist)
    sorted_zipped_lists = sorted(zipped_lists, reverse=True)
    cleanresult = []
    for t in sorted_zipped_lists:
        cleanresult.append(tuple([x for x in t if not t.index(x) == 0]))
    return cleanresult
def update_comp(data, dbclient):
    current_time = time.time()
    try:
        print(data['other']['startcomptime'])
        if (int(data['other']['startcomptime']) > current_time) or (int(data['other']['endcomptime']) < current_time):
            #print('not updating')
            return data
    except:
        if int(data['other']['endcomptime']) < current_time:
            return data
    print("updating")
    old = copy.deepcopy(data)
    collection = dbclient.db.test
    other = data['other']
    players = data['players']
    team = other['team']
    updated_players = data['players']
    if round(time.time()) >= other['endcomptime']:
        return data
    page = team_data(team)
    try:
        info = json.loads(page)
    except:
        return data
    try:
        for user in players:
            for elem in info['results']['members']:
                if user['username'] == elem['username']:
                    try:
                        typed = float(elem['typed'])
                        secs = float(elem['secs'])
                        errs = float(elem
                        ['errs'])
                    except:
                        typed = 0
                        secs = 0
                        errs = 0
                    user['ending-races'] = elem['played']
                    user['total-races'] = user['ending-races'] - user['starting-races']
                    user['display'] = elem['displayName']
                    user['stillinteam'] = True
                    user['ending-typed'] = typed
                    user['ending-secs'] = float(secs)
                    user['ending-errs'] = errs
                    try:
                        user['wpm'] = (user['ending-typed']-user['starting-typed'])/5/float(user['ending-secs']-user['starting-secs'])*60
                        user['accuracy'] = 100-(((user['ending-errs']-user['starting-errs'])/(user['ending-typed']-user['starting-typed']))*100)
                        #user['points'] = user['total-races']*(100+(user['wpm']/2))*user['accuracy']/100
                    except:
                        user['wpm'] = 0
                        user['accuracy'] = 0
                        user['points'] = 0
                    break
            else:
                user['stillinteam'] = False
        res = [ sub['username'] for sub in players ]
        for elem in info['results']['members']:
            if elem['username'] in res:
                continue
            else:
                updated_players.append({
                    "username": elem['username'],
                    "starting-races": elem['played'],
                    "ending-races": elem['played'],
                    "total-races": 0,
                    "display": elem['displayName'] or elem['username'],
                    "stillinteam": True,
                    "starting-typed": elem['typed'],
                    "ending-typed": elem['typed'], 
                    "starting-secs": float(elem['secs']), 
                    "ending-secs": float(elem['secs']),
                    "starting-errs": (elem['errs']), "ending-errs": (elem['errs'])
                })
    except Exception as e:
        return
    #data['players'] = updated_players
    dbclient.update_array(collection, old, data)
    return data
def create_comp(compid, team, startcomptime, endcomptime, user, no_data):
    dbclient = DBClient()
    does_compid_exist = dbclient.get_array(dbclient.db.test, {'compid': str(compid)})
    if does_compid_exist:
        return False, 'Compid already exists!'
    page = team_data(team)
    info = json.loads(page)
    try:
      if request.form['compdesc'] != None:
        compdesc = request.form['compdesc']
      else:
        compdesc = "No Description has been provided."
    except:
      compdesc = "No Description has been provided."
    try:
      print(request.form['public-or-private'])
      public = True
    except:
      public = False
    try:
        info['results']['members']
    except:
        return False, "This team does not exist!"
    results = {
        "results": {
            "compid": str(compid),
            "players": [],
            "other": {}
        }
    }
    for elem in info['results']['members']:
        if elem['displayName'] != None:
            displayname = elem['displayName']
        else:
            displayname = elem['username']
        try:
            typed = elem['typed']
            secs = elem['secs']
            errs = elem['errs']
        except:
            typed = 0
            secs = 0
            errs = 0
        if no_data == False:
            results['results']['players'].append({
            "username": elem['username'],
            "starting-races": elem['played'],
            "ending-races": elem['played'],
            "total-races": 0,
            "display": displayname,
            "stillinteam": True,
            "starting-typed": typed,
            "ending-typed": typed, 
            "starting-secs": float(secs), 
            "ending-secs": float(secs),
            "starting-errs": (errs), "ending-errs": (errs), 
            "wpm": 0,
            "accuracy": 0,
            "points": 0
        })
    results['results']['other'] = {
        "team": team,
        "startcomptime": float(startcomptime),
        "endcomptime": float(endcomptime),
        "author": user,
        "compdesc": compdesc,
        "public": public,
        "ended": False
    }
    dbclient.create_doc(dbclient.db.test, results['results'])
    return True, ""
def find_comps_by_username(username):
    dbclient = DBClient()
    comps = dbclient.db.test.find({'other.author': (username)})
    return comps
  
def find_comps_by_invite(username):
    dbclient = DBClient()
    mcomps = dbclient.db.test.find({'allowed': (username)})
    return mcomps

def find_comps_by_multiplayer(username):
    dbclient = DBClient()
    multicomps = dbclient.db.test.find({'$and': [{'allowed': (username)}, {'other.author': (username)}, {'other.type': 'private'}]})
    return multicomps

def convert_timestamp(timestamp):
    from datetime import date
    dbclient = DBClient()
    endcomptime = dbclient.db.test.find({'other.endcomptime': (timestamp)})
    converted = date.fromtimestamp(endcomptime).strftime('%d %B %Y')
    return converted
def delete_comp(compid, session):
    data, dbclient = get_comp_data(compid)
    creator = str(data['other']['author'])
    if creator == str(session['username']) or data['other']['author'] == str(session['userid']):
        print(dbclient.db.test.delete_one({'compid': str(compid)}).deleted_count)
        return True
    else:
        return False
def get_all_comps(filter={}):
    collection = dbclient.db.test
    return collection.find(filter), dbclient

def bkg_task():
    while True:
        comps, dbclient = get_all_comps({'other.ended': False})
        for x in comps:
            if round(time.time()) < x['other']['endcomptime']:
                update_comp(x, dbclient)
                continue
            else:
                x['other']['ended'] = True
                #update_comp(x, dbclient)
                #dbclient.update_array(dbclient.db.test, comps, x['other']['ended'])
                break
        print('Updated All Comps - '+str(int(time.time())))
        time.sleep(60)

def invite_user(compid, user):
    comp_data, dbclient = get_comp_data(compid)
    try:
        comp_data['allowed'].append(user)
    except:
        comp_data['allowed'] = [user,]
    dbclient.update_array(dbclient.db.test, {"compid": compid}, comp_data)
    return
  
def convert_secs(seconds):
  seconds_in_day = 60 * 60 * 24
  seconds_in_hour = 60 * 60
  seconds_in_minute = 60
  days = seconds // seconds_in_day
  hours = (seconds - (days * seconds_in_day)) // seconds_in_hour
  minutes = (seconds - (days * seconds_in_day) - (hours * seconds_in_hour)) // seconds_in_minute
  secs = (seconds - (days * seconds_in_day) - (hours * seconds_in_hour))%60
  return f"{round(days)} day(s), {round(hours)}:{round(minutes)}:{round(secs)}"
def timestamp(ts):
  
    return convert_secs(ts-time.time())  #rftime("%Y-%m-%d %H:%M:%S", time.localtime(ts-time.time()))

def edit_compdesc(compdesc):
    data, dbclient = get_comp_data(compdesc)
    data = update_compdesc(data, dbclient)
    compdesc = []