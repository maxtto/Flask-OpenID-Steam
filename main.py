from os.path import dirname, join
from flask import Flask, g, redirect, session, json
from flask_sqlalchemy import SQLAlchemy
from flask_openid import OpenID
import urllib, urllib2
import re

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI = 'sqlite:///flask-openid.db',
    SECRET_KEY = 'STEAM API KEY',
    DEBUG = True,
    PORT = 5000
)

oid = OpenID(app, join(dirname(__file__), 'openid_store'))
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_id = db.Column(db.String(40))
    nickname = db.Column(db.String(80))

    @staticmethod
    def get_or_create(steam_id):
        rv = User.query.filter_by(steam_id=steam_id).first()
        if rv is None:
            rv = User()
            rv.steam_id = steam_id
            dbs.session.add(rv)
        return rv


_steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')

def get_steam_userinfo(steam_id):
    options = {
        'key': app.secret_key,
        'steamids': steam_id
    }
    url = 'http://api.steampowered.com/ISteamUser/' \
          'GetPlayerSummaries/v0001/?%s' % urllib.urlencode(options)
    rv = json.load(urllib2.urlopen(url))
    return rv['response']['players']['player'][0] or {}

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.filter_by(id=session['user_id']).first()

@app.route("/login")
@oid.loginhandler
def login():
    if g.user is not None:
        return redirect(oid.get_next_url())
    else:
        return oid.try_login("http://steamcommunity.com/openid")

@oid.after_login
def new_user(resp):
    match = _steam_id_re.search(resp.identity_url)
    g.user = User.get_or_create(match.group(1))
    steamdata = get_steam_userinfo(g.user.steam_id)
    g.user.nickname = steamdata['personaname']
    db.session.commit()
    session['user_id'] = g.user.id
    return redirect(oid.get_next_url())

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(oid.get_next_url())

@app.route('/')
def hello():
    if g.user:
        return "Hi user %s with steam id %s <a href='/logout'>logout</a>" % (g.user.nickname, g.user.steam_id)
    else:
        return "You are not logged in <a href='/login'>login</a>"

if __name__ == "__main__":
    app.run()
