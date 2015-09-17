#pylint: skip-file
oauths = []
apis = []
returnid = None

def clear():
    oauths = []
    apis = []
    returnid = None


class Status(object):
    def __init__(self, id):
        self.id = id


class OAuthHandler(object):
    def __init__(self, consumer_key, consumer_secret):
        self.access_token = None
        self.access_token_secret = None
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        global oauths
        oauths.append(self)

    def set_access_token(self, access_token, access_token_secret):
        self.access_token = access_token
        self.access_token_secret = access_token_secret
    

class API(object):
    def __init__(self, oauth):
        self.status = None
        self.oauth = oauth
        global apis
        apis.append(self)
        
    def update_status(self, status):
        self.status = status
        return Status(returnid)

