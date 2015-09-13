import os
import shutil

from flask.ext.testing import TestCase
from mock import Mock, patch
from whoosh.fields import KEYWORD, TEXT

from yawt import create_app
from yawt.cli import create_manager, Walk
from yawt.test import TempFolder
from yawt.utils import call_plugins
from yawtext.autotags import Autotag
from yawtext.vc import ChangedFiles


HAMLET = """---
---
this is hamlet, by shakespeare.  He waited too long for stuff.
Something about the whole experience rubbed me the wrong way. An easy
explanation would be the death metal music playing on the speakers,
but I don't think that was it. I'm not a fan of death metal, but I'm
not *anti* death metal either. Maybe it was the art on the wall. There
was one of white clothes on a clothesline splattered in blood, another
of a man wailing whilst holding his dead son in his arms, and yet
another of some sort of crime/death scene, with blood pooled on the
ground. Are you detecting a theme? So was I. 
"""

MADRAS = """---
tags: food,spicy
---
This is a very spicy dish with beef.
So I tried another batch of tonic water this year with no all-spice or
lemongrass, and a bit less citric acid.  I also simplified the recipe
somewhat, using plain sugar instead of agave syrup and omitting the citrus
juice (though keeping the zest).
The result is simpler to make and, in my opinion, better than the previous
batch.  I think it pairs better with a good gin since there's less in the
tonic water to compete with the spirit.
"""

SOUP = """---
tags: food,liquid
---
Food, but you can drink it!
My traditional ratio for a "sour" cocktail is 6/2/1.  That's 6 parts base, 2
parts lemon or lime, and 1 part 2-1 sugar syrup.  In concrete terms that
translates into 6cl of liquor, 2cl of lemon/lime and 2tsp of sugar syrup.
This yields a very sour, somewhat sweet drink, where the base can still
shine through.
The liquor is quite clearly the main flavour in such a cocktail.  In fact, I
hesitate to call it a "sour" since it's not actually very sour.  The citrus
is definitely there, but it complements and supports the liquor rather than
overpowering it.
"""

SPAGHETTI = """---
---
pasta with tomato sauce
That's not to say I don't respect doctors, lawyers and copy-editors;
of course I do. I'm not that narrow-sighted, and I obviously know that
it has to be *someone*'s job to know the human body, or Canada's law
system, or how to spell. And I'm not claiming that laws are
complicated *simply* so that lawyers can have a job. I'm aware of the
dangers of ambiguous language, and I'm aware of the need to create a
specialized jargon for something as important as the rules of
society. And I'm aware that one should spell one's words correctly in
formal situations if one wishes to avoid looking like an idiot. And
I'm obviously aware of the value of doctors. But factor in the sheer
*randomness* of it all and, well, It's just not something I can
imagine enjoying myself.
"""

LINGUINE = """---
tags: italian,pasta
---
pasta with tomato sauce
That's not to say I don't respect doctors, lawyers and copy-editors;
of course I do. I'm not that narrow-sighted, and I obviously know that
it has to be *someone*'s job to know the human body, or Canada's law
system, or how to spell. And I'm not claiming that laws are
complicated *simply* so that lawyers can have a job. I'm aware of the
dangers of ambiguous language, and I'm aware of the need to create a
specialized jargon for something as important as the rules of
society. And I'm aware that one should spell one's words correctly in
formal situations if one wishes to avoid looking like an idiot. And
I'm obviously aware of the value of doctors. But factor in the sheer
*randomness* of it all and, well, It's just not something I can
imagine enjoying myself.
"""

class TestFolder(TempFolder):
    def __init__(self):
        super(TestFolder, self).__init__()
        self.files = {
            'content/reading/hamlet.txt': HAMLET,
            'content/cooking/indian/madras.txt': MADRAS,
            'content/cooking/soup.txt': SOUP,
        }


class TestAutotagInitialization(TestCase):
    YAWT_EXTENSIONS = ['yawtext.autotags.YawtAutotags']

    def create_app(self):
        return create_app('/tmp/blah', config=self)

    def test_autotag_is_added_to_commands(self):
        self.app.preprocess_request()
        manager = create_manager(self.app)
        self.assertTrue('autotag' in manager._commands)


class TestAutotags(TestCase):
    YAWT_META_TYPES = {'tags': 'list'}
    YAWT_EXTENSIONS = ['flask_whoosh.Whoosh',
                       'yawtext.indexer.YawtIndexer',
                       'yawtext.autotags.YawtAutotags']
    WHOOSH_INDEX_ROOT = '/tmp/whoosh/index'
    YAWT_INDEXER_WHOOSH_INFO_FIELDS = {'tags': KEYWORD()}
    YAWT_INDEXER_WHOOSH_FIELDS = {'content': TEXT(vector=True)}

    def create_app(self):
        self.site = TestFolder()
        self.site.initialize()
        return create_app(self.site.site_root, config=self)

    def test_autotags_adjusts_tags(self):
        with self.app.app_context():
            walk = Walk()
            walk.run()
        self.site.save_file('content/cooking/italian/spaghetti.txt', SPAGHETTI)
        changed = ChangedFiles(added=['content/cooking/italian/spaghetti.txt'])

        mock = Mock(return_value='')
        with patch('__builtin__.raw_input', mock):
            call_plugins('on_pre_sync', changed)

        self.assertIn('tags:',
                       self.site.load_file('content/cooking/italian/spaghetti.txt'))

    def test_autotags_leaves_existing_tags_alone(self):
        with self.app.app_context():
            walk = Walk()
            walk.run()
        self.site.save_file('content/cooking/italian/linguine.txt', LINGUINE)
        changed = ChangedFiles(added=['content/cooking/italian/linguine.txt'])

        mock = Mock(return_value='')
        with patch('__builtin__.raw_input', mock):
            call_plugins('on_pre_sync', changed)

        self.assertIn('tags: italian,pasta',
                       self.site.load_file('content/cooking/italian/linguine.txt'))

    def test_autotags_honours_tag_override(self):
        with self.app.app_context():
            walk = Walk()
            walk.run()
        self.site.save_file('content/cooking/italian/spaghetti.txt', SPAGHETTI)
        changed = ChangedFiles(added=['content/cooking/italian/spaghetti.txt'])

        mock = Mock(return_value='orange,apple')
        with patch('__builtin__.raw_input', mock):
            call_plugins('on_pre_sync', changed)

        self.assertIn('tags: orange,apple',
                       self.site.load_file('content/cooking/italian/spaghetti.txt'))

    def test_autotags_command_adds_tags_to_existing_file(self):
        with self.app.app_context():
            walk = Walk()
            walk.run()

        self.assertNotIn('tags:',
                         self.site.load_file('content/reading/hamlet.txt'))
        autotag = Autotag()
        autotag.run(edit=True, article='content/reading/hamlet.txt')

        self.assertIn('tags:',
                       self.site.load_file('content/reading/hamlet.txt'))

    def tearDown(self):
        if os.path.exists('/tmp/whoosh/index'):
            shutil.rmtree('/tmp/whoosh/index')
        self.site.remove()
