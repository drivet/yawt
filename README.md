yawt
====
[![Build Status](https://travis-ci.org/drivet/yawt.svg?branch=master)](https://travis-ci.org/drivet/yawt)
[![Coverage Status](https://coveralls.io/repos/drivet/yawt/badge.svg?branch=master)](https://coveralls.io/r/drivet/yawt?branch=master)

YAWT is Yet Another Weblog Tool, written in python. It's a blogging/CMS
engine in the style of blohg, jekyll and other DVCS based blogging tools.

The idea is that you store your blog entries in a DVCS and we use that
metadata to glean information like the post time, last modification time,
and author.  

yawt sports a plugin architecture and comes with plugins to support features
such as tags, archives, full text search, and markdown support.  DVCS
support included git and mercurial for the metadata support.
