"""Module for posting to facebook"""
import os
import facepy
from yawt.utils import cfg, load_file


def post_fb(post, link=None):
    """Post message to facebook"""
    token_file = os.path.expanduser(cfg('YAWT_MICROPOST_FB_ACCESS_TOKEN_FILE'))
    access_tok = load_file(token_file)
    graph = facepy.GraphAPI(access_tok)

    if link:
        print("trying force facebook to scrape URL...")
        graph.post('/', id=link, scrape=True)
        print("trying to post to facebook...")
        response = graph.post('me/feed', message=post, link=link)
    else:
        response = graph.post('me/feed', message=post)
    print("response: "+str(response))
    fid = None
    retid = response['id']
    if retid:
        pids = retid.split('_')
        if len(pids) < 2:
            print("unexpected id format")
        fid = pids[1]
    posturl = cfg('YAWT_MICROPOST_FB_POST_URL')
    metadata = {}
    if fid:
        metadata['fbpost'] = posturl.format(fid)
    return metadata
