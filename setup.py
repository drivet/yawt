"""
yawt
----

YAWT is Yet Another Weblog Tool, written in python. It's a blogging/CMS
engine in the style of blohg, jekyll and other DVCS based blogging tools.

"""
from setuptools import setup


setup(
    name='yawt',
    version='0.1',
    url='https://github.com/drivet/yawt/',
    license='MIT',
    author='Desmond Rivet',
    author_email='desmond.rivet@gmail.com',
    description='YAWT is Yet Another Weblog Tool',
    long_description=__doc__,
    packages=['yawt', 'yawtext'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask',
        'Flask-Script',
        'blinker',
        'Markdown',
        'jsonpickle',
        'python-dateutil',
        'Pygments',
        # Whoosh 2.7.0 breaks my tests for some reason.
        'Whoosh<=2.6.0'
        'Flask-Whoosh',
        'BeautifulSoup4',
        'PyYAML',
        'python-frontmatter',
        'pytz',
        'tweepy',
        'facepy',
        'py-gfm'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Software Development :: Version Control',
    ],
    scripts=['bin/yawt'],
)
