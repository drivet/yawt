default_article_template = """<html>
    <head>
        <title>{{ article.info.title }}</title>
    </head>
    <body>
        <h1>{{article.info.title}}</h1>
        <p>Posted on {{article.info.create_time|dateformat('%Y/%m/%d %H:%M')}} at
               {{article.info.fullname}}</p>
        <p>Last modified on {{article.info.modified_time|dateformat('%Y/%m/%d %H:%M')}}</p>
        <p>{{article.content}}</p>
    </body>
</html>
"""

default_404_template = """<html>
    <head>
        <title>Not found</title>
    </head>
    <body>
        <p>Not found</p>
    </body>
</html>
"""
