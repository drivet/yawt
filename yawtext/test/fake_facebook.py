#pylint: skip-file
graphapis = []
returnval = None

def clear():
    graphapis = []
    returnval = None


class GraphAPI(object):
    def __init__(self, access_token):
        self.access_token = access_token
        global graphapis
        graphapis.append(self)

    def post(self, target, message):
        self.target = target
        self.message = message
        return returnval
