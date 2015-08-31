import tweepy

def get_api(cfg):
    auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
    auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
    return tweepy.API(auth)

def main():
    # Fill in the values noted in previous step here
    cfg = { 
        "consumer_key"        : "a1k1NiNBUI0yy2HjXZmKNyNVA",
        "consumer_secret"     : "WIeUPgSXUM62DczZUU0KUX7WTJEfw0PmOYrUP2JU35YMV7PbOs",
        "access_token"        : "3131387374-AWYepkgN2oe6pCNNQDXim7OErYdn7dIi1hJRlta",
        "access_token_secret" : "aCbMaRUFZP33hFdH5Fthj3FaYl0ifxssgnEdX59t3q6m2" 
    }

    api = get_api(cfg)
    tweet = "Repeating the Facebook experiment. Sending out a tweet from a python app.  Can you see me? :)"
    status = api.update_status(status=tweet) 
    # Yes, tweet is called 'status' rather confusing
    print str(status)

if __name__ == "__main__":
    main()
