'''
Created on Jul 9, 2012
Author: George Lifchits
'''

import discogs_client as discogs
import pprint as p

discogs.user_agent = 'test/glifchits'

artist = discogs.Artist('kraftwerk')
print artist

p.pprint (artist.data)
