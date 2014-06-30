#encoding=utf-8
'''
Created on Apr 8, 2012
Author: George Lifchits
'''

import discogs_client as discogs
from constants import *
import re
import pickle
import win32com.client
from copy import deepcopy as copy
import codecs
from requests.exceptions import ConnectionError
import time
import threading


class Track(object):
    '''
    A Discogs track object
    Modelled after iTunes SDK track object
    '''

    def __init__(self,
                 Name = None,
                 Artist = None,
                 Composer = None,
                 Genre = None,
                 AlbumArtist = None,
                 Album = None,
                 Grouping = None,
                 Comments = None,
                 Year = None,
                 TrackNumber = None,
                 TrackCount = None,
                 DiscNumber = None,
                 DiscCount = None):

        self.Name = Name
        self.Artist = Artist
        self.Composer = Composer
        self.Genre = Genre
        self.AlbumArtist = AlbumArtist
        self.Album = Album
        self.Grouping = Grouping
        self.Comments = Comments
        self.Year = Year
        self.TrackNumber = TrackNumber
        self.TrackCount = TrackCount
        self.DiscNumber = DiscNumber
        self.DiscCount = DiscCount

    def __str__(self):
        '''
        Prints relevant information for an iTunes or Discogs track
        '''
        info = {'tn': self.TrackNumber,
                'tc': self.TrackCount,
                'dn': self.DiscNumber,
                'dc': self.DiscCount,
                'n': self.Name,
                'a': self.Artist,
                'c': self.Composer}

        return '{tn:>3}/{tc:<2} {dc:>2}/{dn:<3} {a} - {n}\n              ({c})'\
                .format(**info)

    def __cmp__(self, other):
        '''
        Comparison function for tracks: only compares track/disc position
        '''
        if self.DiscNumber > other.DiscNumber:
            return 1
        elif self.DiscNumber < other.DiscNumber:
            return -1
        else:
            if self.TrackNumber > other.TrackNumber:
                return 1
            elif self.TrackNumber < other.TrackNumber:
                return -1
            else:
                return 0


class DiscogsTracklist(object):
    '''
    Using any valid Discogs release ID, generates a tracklist of metadata
    retrieved from that Discogs ID.
    
    Class contains multiple functions which manipulate data retrieved from the
    API which are used to build this list.
    '''

    def __init__(self, release_id):
        discogs.user_agent = 'test/glifchits'

        self.utils = Utilities()
        self.real_name = RealName()

        self.itunesinfo = ItunesInfo()
        self.itunes_genres = self.itunesinfo.get_genres()
        self.itunes_labels = self.itunesinfo.get_labels()

        self.featuringroles = ('featuring', 'vocals')
        self.composerinclude = ('written', 'lyrics', 'music')
        self.composerexclude = ()

        self.anv_preferred = True

        self.release = discogs.Release(release_id)
        try:
            self.release.data
        except:
            raise

        try:
            self.master = discogs.MasterRelease(self.release.data['master_id'])
        except KeyError:
            self.master = None

        self.release_tracklist = self.get_discogs_raw_tracklist()

        # Universal release info
        # this stuff is the same for all tracks in a release.
        self.album = self.get_album_name()
        self.album_artist = self.get_album_artist()
        self.release_composers = self.get_release_credits_people()['writers']
        self.release_featured = self.get_release_credits_people()['featured']
        self.year = self.get_year()
        self.grouping = self.get_label()
        self.discogs_id = self.get_discogsid()
        self.tracklisting = self.get_track_position_listing()
        self.genre = self.get_genre()
        self.disc_total = self.get_disc_total()

        # This is the money maker.
        self.discogs_tracklist = self.get_release_info()

    def get_release_info(self):
        complete = False

        while not complete:
            try:
                discogs_tracklist = []

                count = 0
                for track in self.release_tracklist:
                    count += 1
                    position = track['position']

                    name = self.fix_name(self.get_name(track))
                    artist = self.get_artist(track, position)
                    composer = self.get_writers(track, position)
                    genre = self.genre
                    a_artist = self.album_artist
                    album = self.album
                    grouping = self.grouping
                    comments = "D:" + self.discogs_id
                    year = self.year
                    track_this = self.get_track_this(count)
                    disc_this = self.get_disc_this(count)
                    track_total = self.get_track_total(disc_this)
                    disc_total = self.disc_total

                    new_track = Track()
                    new_track.Name = name
                    new_track.Artist = artist
                    new_track.Composer = composer
                    new_track.Genre = genre
                    new_track.AlbumArtist = a_artist
                    new_track.Album = album
                    new_track.Grouping = grouping
                    new_track.Comments = comments
                    new_track.Year = year
                    new_track.TrackNumber = track_this
                    new_track.DiscNumber = disc_this
                    new_track.TrackCount = track_total
                    new_track.DiscCount = disc_total

                    discogs_tracklist.append(new_track)
                print ''
                complete = True

            except ConnectionError:
                print 'Connection timed out. Trying again in 10 seconds.'
                time.sleep(10)

        return discogs_tracklist

    '''
    INFO RETRIEVAL FUNCTIONS
    '''

    def update_itunes_library_data(self):
        self.itunesinfo.update_info()
        self.genres = self.itunesinfo.get_genres()
        self.labels = self.itunesinfo.get_labels()
        return

    def include_producer(self):
        if self.utils.values_in_tuple(self.release.data['genres'], ('electronic', 'hip hop')):
            self.composerinclude += ('producer',)
            self.composerexclude += ('producer [', 'executive producer')
        return

    def get_discogs_raw_tracklist(self):
        tlist = self.release.data['tracklist']

        # filters out 'index' tracks which are of no relevance to iTunes
        return filter(lambda track: track['position'] != '', tlist)

    def get_release_credits_people(self):
        writers = []
        featured = []

        for artist in self.release.data['extraartists']:
            if self.utils.values_in_tuple(artist['role'], self.composerinclude, self.composerexclude):
                writers.append(artist)

            if self.utils.values_in_tuple(artist['role'], self.featuringroles):
                featured.append(artist)

        return {'writers': writers, 'featured': featured}

    def get_album_artist(self):
        artist_list = []
        feat_list = []
        feat = False
        for artist in self.release.data['artists']:
            if self.anv_preferred:
                name = artist['anv']
                get_name = name == ''

            if not self.anv_preferred or get_name:
                name = artist['name']

            name = [self.utils.fix_discogs_string(name)]

            if feat:
                feat_list += name
                feat = False
            else:
                artist_list += name

            feat = self.utils.values_in_tuple(artist['join'], ('feat', 'with'))

        artist_string = self.utils.concat_list(artist_list)
        feat_string = self.utils.concat_list(feat_list) # concatenate the featured list

        if feat_string != '': # if there ARE featured artists then add 'feat.' before the list
            feat_string = " feat. " + feat_string

        return artist_string + feat_string

    def get_year(self):
        if self.master is None:
            return self.release.data['year']
        else:
            return self.master.data['year']

    def get_label(self):
        if len(self.release.data['labels']) > 1:
            temp = {}

            for label in self.release.data['labels']:
                labelname = label['name']

                if labelname in self.itunes_labels.keys():
                    temp[labelname] = self.itunes_labels[labelname]
                else:
                    temp[labelname] = 1

            highest = 0
            highest_count = 0
            for i in range(len(temp.keys())):
                label = temp.keys()[i]

                if temp[label] > highest_count:
                    highest = i
                    highest_count = temp[label]

            labelname = temp.keys()[highest]
        else:
            labelname = self.release.data['labels'][0]['name']

        return self.utils.fix_discogs_string(labelname)

    def get_genre(self):
        #genres = self.release.data['genres']
        #styles = self.release.data['styles']
        return None

    def get_discogsid(self):
        # kind of redundant since the user must input the ID, but I guess more legitimate
        return str(self.release.data['id'])

    def get_album_name(self):
        return self.release.data['title']

    def get_track_position_listing(self):
        '''
        this goes through the tracklist and creates an index of the track POSITIONS:
        uses ridiculous methods to count the number of discs used, number of tracks in a disc
        mostly necessary because vinyl track numbers are fucking impossible to deal with
        also very easy to get track/disc counts by requesting the last element in this list
        '''
        tracklist = self.release_tracklist

        tracklisting = []

        prev_disc = -1
        count = 0
        for track in tracklist:
            count += 1
            d = self.utils.track_and_disc(track['position'])[1]
            if prev_disc < d:
                count = 1
                prev_disc = d
            tracklisting.append((count, copy(d)))

        return tracklisting

    def get_name(self, track):
        return track['title']

    def fix_name(self, name):
        name = name.replace('Rmx', 'Remix')

        for thing in [' (Original Mix)', ' (Original)']:
            name = name.replace(thing, '')

        return name

    def get_artist(self, track, position):
        artist_list = []
        feat_list = []
        feat = False
        if 'artists' in track.keys():
            for artist in track['artists']:
                if self.anv_preferred:
                    name = artist['anv']
                    get_name = name == ''

                if not self.anv_preferred or get_name:
                    name = artist['name']

                name = [self.utils.fix_discogs_string(name)]

                if feat:
                    feat_list += name
                    feat = False
                else:
                    artist_list += name

                feat = self.utils.values_in_tuple(artist['join'], ('feat', 'with'))
            #artist_string = self.utils.concat_list(artist_list)
        else:
            artist_list.append(self.album_artist)
            # the function used to retrive album artist data already went through the crazy 'featuring' process

        if 'extraartists' in track.keys(): # checks for featured artists in the extraartist key
            for artist in track['extraartists']:
                if self.utils.values_in_tuple(artist['role'], self.featuringroles):
                    feat_list.append(artist)

        cf = self.utils.compare_track_numbers
        for artist in self.release_featured:
            if artist['tracks'] != '': # this artist has credits for specific tracks -- find this one
                track_positions = artist['tracks'].split(', ')
                for pos in track_positions:
                    first, last = self.utils.track_range(pos)
                    if cf(first, position) <= 0 and cf(last, position) >= 0:
                        feat_list.append(artist)
                        break

        temp = []
        for artist in feat_list:
            if self.anv_preferred and artist['anv'] != '':
                temp.append(artist['anv'])
            else:
                temp.append(artist['name'])

        if temp is not []:
            # in case the featured artist is both in the track artist AND extraartist key
            feat_list = list(set(temp))

        feat_list = map(lambda name: self.utils.fix_discogs_string(name), feat_list)

        # sometimes a main artist is also featured (DJ Mehdi & Fafi feat. Fafi)
        feat_list = filter(lambda name: name not in artist_list, feat_list)

        artist_string = self.utils.concat_list(artist_list)
        feat_string = self.utils.concat_list(feat_list)


        if feat_string != '': # if there ARE featured artists then add 'feat.' before the list
            feat_string = " feat. " + feat_string

        return artist_string + feat_string

    def thread_get_name(self, name, output_list):
        real_name = self.real_name.get(name)
        output_list += real_name

    def get_writers(self, track, position):
        cf = self.utils.compare_track_numbers
        writers = []
        if 'extraartists' in track.keys(): # extract writers from extraartist key in track
            for writer in track['extraartists']:
                if self.utils.values_in_tuple(writer['role'], self.composerinclude, self.composerexclude):
                    writers.append(writer)

        for writer in self.release_composers: # get writers relevant to this track from global credits
            if writer['tracks'] != '': # this writer has credits for specific tracks -- find this one
                track_positions = writer['tracks'].split(', ')
                for pos in track_positions:
                    first, last = self.utils.track_range(pos)
                    if cf(first, position) <= 0 and cf(last, position) >= 0:
                        writers.append(writer)
                        break
            else: # no specific tracks -> all tracks -> this one counts
                writers.append(writer)

        if writers == [] and 'artists' in track.keys(): # no actual writers listed: use names of track artists
            writers += track['artists']

        if writers == []: # no track artists either: get global artists
            writers += self.release.data['artists']

        real_names = []
        '''for writer in writers:
            real_name = self.real_name.get(writer['name'])
            real_names += real_name'''

        threads = []
        for writer in writers: # now we have a list of strings; could be names, could be artist aliases -- get real names
            thread = threading.Thread(target = self.thread_get_name, args = (writer['name'], real_names))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        return self.utils.concat_list(real_names, '/')

    def get_track_this(self, count):
        return self.tracklisting[count - 1][TRACK]

    def get_track_total(self, disc):
        i = 0
        while i < len(self.tracklisting) and self.tracklisting[i][DISC] == disc:
            i += 1

        return self.tracklisting[i - 1][TRACK]

    def get_disc_this(self, count):
        return self.tracklisting[count - 1][DISC]

    def get_disc_total(self):
        return self.tracklisting[-1][DISC]


class ItunesInfo(object):
    '''
    Small set of functions which gets some information about the user's
    iTunes library. PyTunesFixer prefers a label name which already exists in
    the user's library. Right now it also gets genre info, but this isn't
    used yet.
    '''

    def __init__(self):
        iTunes = win32com.client.gencache.EnsureDispatch("iTunes.Application")
        self.library = iTunes.LibraryPlaylist.Tracks
        self.genre_file = 'genres.pkl'
        self.label_file = 'labels.pkl'
        self.genres = {}
        self.labels = {}

    def update(self, d, key):
        if key not in d.keys():
            d[key] = 1
        else:
            d[key] += 1
        return

    def update_info(self):
        print "Getting information from iTunes Library"

        for track in self.library:
            try:
                print track.Name
            except:
                print 'fail'
            try:
                genre = track.Genre
            except:
                genre = None
                print 'failed to retrieve genre'
            try:
                label = track.Grouping
            except:
                label = None
                print 'failed to retrieve label'

            self.update(self.genres, genre)
            self.update(self.labels, label)

        genre_pickle = open(self.genre_file, 'wb')
        label_pickle = open(self.label_file, 'wb')

        pickle.dump(self.genres, genre_pickle)
        pickle.dump(self.labels, label_pickle)

        genre_pickle.close()
        label_pickle.close()
        return

    def print_d(self, d):
        keys = d.keys()

        while keys != []:
            highest = 0
            highest_key = 0

            for i in range(len(keys)):
                key = keys[i]
                count = d[key]

                if count > highest:
                    highest_key = i
                    highest = count

            print "{0:40} {1}".format(keys[highest_key], highest)
            keys.pop(highest_key)

    def get_genres(self):
        genre_pickle = open(self.genre_file, 'rb')
        genres = pickle.load(genre_pickle)
        genre_pickle.close()
        return genres

    def get_labels(self):
        label_pickle = open(self.label_file, 'rb')
        labels = pickle.load(label_pickle)
        label_pickle.close()
        return labels


class RealName(object):
    '''
    The 'get' function is useful. It gets (a) real name(s) from an artist name.
    '''

    def __init__(self, exceptions_file = 'realname_exceptions.txt'):
        self.utils = Utilities()
        self.exceptions = self.read_exceptions(exceptions_file)
        self.artist_cache = {}

    def read_exceptions(self, exceptions_file):
        exceptions = {}
        f = codecs.open(exceptions_file, encoding = 'utf-8')
        contents = f.read()
        f.close()
        contents = contents.replace('\r', '')
        contents = contents.split('\n')
        contents = filter(lambda line: line[0].startswith('#') == False,
                          contents)
        assert len(contents) % 2 == 0
        for i in range(len(contents)):
            if i % 2 == 0:
                exceptions[contents[i]] = contents[i + 1]
        return exceptions

    def fix(self, name):
        '''
        Consumes a name and then converts it to a better name.
        Also requires 'exceptions', data from the 'realname_exceptions.txt' file
        ie. Guillaume Emmanuel de Homem-Christo
             -> Guy-Manuel de Homem-Christo (in list of exceptions)
        ie. Norman Quentin Cook (born Quentin ...blah blah... 2002)
             -> Norman Cook
        '''
        # process any possible listed exception
        exempted = False
        for exception in self.exceptions:
            if exception[0] == name:
                result = exception[1]
                exempted = True

        if not exempted:
            # this removes any type of bullshit in brackets
            i = len(name)
            while i >= 0:
                name = name[:i]
                i = name.find(' (')

            # surname prefixes: ensures Armand van Helden is not Armand Helden
            prefix = ('dal', 'de', 'der', 'des', 'dos', 'du', 'le', 'van')

            # want to make sure Jr. gets due credit
            at_end = ('Jr.', 'Jr', 'Sr.', 'Sr', 'II', 'III', 'IV', 'V')

            fullname = name.split(' ')
            if len(fullname) > 1:
                first_name = fullname.pop(0)
                first_name = first_name[0].upper() + first_name[1:]
                last_name = fullname.pop(-1)
                last_name = last_name[0].upper() + last_name[1:]
                # I know .capitalize() exists. But it made 
                # Mehdi Faveris-Essadi turn into Mehdi Faveris-essadi

                while last_name in at_end:
                    last_name = fullname.pop(-1) + ' ' + last_name

                middle = []
                for name in fullname:
                    if name.lower() in prefix:
                        middle += [name]

                fullname = [first_name] + middle + [last_name]

            result = self.utils.concat_list(fullname, ' ', False)

        return result

    def get(self, writer):
        if writer in self.artist_cache.keys():
            artist = self.artist_cache[writer]
        else:
            artist = discogs.Artist(writer)
            self.artist_cache[writer] = artist
            print '.',

        if artist.name == 'Various':
            result = ['']
        else:
            adata = artist.data
            if 'members' in adata.keys():
                result = []
                for artist in adata['members']:
                    result += self.get(artist)
            elif 'realname' in adata.keys():
                result = []
                for name in re.split(' & |, ', adata['realname']):
                    result += [self.fix(name.strip())]
            else:
                result = [self.utils.fix_discogs_string(adata['name'])]

        return result


class Utilities(object):
    '''
    Some random utilities this program uses.
    '''

    def concat_list(self, the_list, join_str = None, sort = True):
        '''
        Take a list and concatenates it to a string.
        Delimits items with :join_str:. If no :join_str: defined, delimits
        as a list; comma-separated with final & ('a, b, c & d')
        '''
        if sort:
            the_list = list(set(the_list))
            the_list.sort()

        try:
            output = str(the_list.pop(0))
        except:
            return ''

        if join_str is None:
            while len(the_list) > 1:
                output += ', ' + str(the_list.pop(0))
            if len(the_list) == 1: # necessary for singleton list case
                output += ' & ' + str(the_list.pop(0))
        else:
            while len(the_list) > 0:
                output += join_str + str(the_list.pop(0))

        return output

    def values_in_tuple(self, values, include, exclude = ()):
        '''    
        if an element of include is in an element of values, returns True
        unless an element of exclude is in an element of values, returns False
        if no elements of include are in an element of values, returns False
        '''
        make_set = lambda lst: set(map(lambda item: item.lower(), lst))
        values = make_set(values)
        include = make_set(include)
        exclude = make_set(exclude)
        return len(values & include) > 0 and len(values & exclude) == 0

    def fix_discogs_string(self, name):
        '''
        Removes those numbers in brackets Discogs uses to distinctify duplicates
        Puts a ', The' suffix at the beginning
        '''
        if ' (' in name and name.endswith(')'):
            i = name.find(' (')
            if name[i + 2:len(name) - 1].isdigit():
                name = name[:i]

        if name.endswith(', The'):
            name = "The " + name[:name.find(', The')]

        return name

    def track_and_disc(self, track, this_disc = 1, last_side_tracks = 0):
        '''
        track = '1' -> {track: 1, disc: 1}
        track = '2-13' -> {track: 13, disc: 2}
        track = 'C2' -> {track: 2, disc: 2}
        track = 'B3', last_side = 3 -> {track: 6, disc: 1}
        '''
        track = str(track)
        if track[0].isdigit():
            if '-' in track:
                td = track.split('-')
                r_track = int(td[1])
                r_disc = int(td[0])
            else:
                r_track = int(track)
                r_disc = int(this_disc)
        else:
            # mapping for vinyl side letter to disc number integer
            # ie: A = 1, B = 1, C = 2, D = 2, for all 26 letter characters
            r_disc = (ord(track[0].upper()) - 65 - \
                     (ord(track[0].upper()) - 65) % 2) // 2 + 1

            if len(track) > 1 and track[1:].isdigit():
                track_s = int(track[1:])
            else:
                track_s = 1

            r_track = track_s + last_side_tracks

        return r_track, r_disc

    def track_range(self, positions):
        '''
        1 to 4 -> (1,4)
        2 -> (2,2)
        A2 to B4 -> (A2, B4)
        '''
        positions = str(positions)
        if ' to ' in positions:
            x, y = positions.split(' to ')
            try:
                x, y = int(x), int(y)
            except:
                pass
            result = (x, y)
        else:
            x = positions
            try:
                x = int(x)
            except:
                pass
            result = (x, x)
        return result

    def compare_track_numbers(self, track1, track2):
        track_1, disc_1 = self.track_and_disc(track1)
        track_2, disc_2 = self.track_and_disc(track2)

        if disc_1 > disc_2:
            result = GREATER
        elif disc_1 < disc_2:
            result = LESSER
        else:
            if track_1 > track_2:
                result = GREATER
            elif track_1 < track_2:
                result = LESSER
            else:
                result = EQUALS
        return result
