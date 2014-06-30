#encoding=utf-8
'''
Created on Jun 9, 2012
Author: George Lifchits

This is the main interface for PyTunesFixer.

PyTunesFixer goes between iTunes COM APIs and the Discogs API to get
detailed metadata from Discogs.com and systematically apply it to 
iTunes library music.
'''

from discogs_tracklist import DiscogsTracklist
import win32com.client
import time
import sys
import difflib
import logging

log = logging.getLogger('PyTunesFixer')

def connect_to_itunes():
    try:
        log.info('Starting/connecting to iTunes...')
        iTunes = win32com.client.gencache. \
                 EnsureDispatch('iTunes.Application')
        log.info('Done.')
        return iTunes
    except:
        log.error('Connection failed. Application terminated.')
        sys.exit()


class FixiTunesFromID(object):

    def __init__(self):
        self.iTunes = connect_to_itunes()
        rel_id = self.get_release_id()
        discogs = DiscogsTracklist(rel_id)
        self.discogs_tracklist = discogs.get_release_info()
        self.utils = FixerUtilities()
        self.start_tool()

    def get_release_id(self):
        try:
            rel_id = int(raw_input('Enter Discogs release ID: ').strip())
        except:
            log.info('Invalid release ID. Try again.')
            rel_id = self.get_release_id()

        return rel_id

    def get_selected(self):
        itunes_tracklist = []
        while itunes_tracklist == []:
            raw_input('Select tracks in iTunes (any key to continue)')

            selected = self.iTunes.SelectedTracks
            if selected is not None:
                for track in selected:
                    itunes_tracklist.append(track)

                if len(itunes_tracklist) != len(self.discogs_tracklist):
                    cont = raw_input("\nTracklists are not same length! \
                                      \n('y' to continue, any other key to \
                                      \nselect new iTunes tracks)".strip())
                    if cont != 'y':
                        itunes_tracklist = []
            else:
                log.info('Nothing selected in iTunes')

        itunes_tracklist.sort(key = lambda t: (t.DiscNumber, t.TrackNumber))
        return itunes_tracklist

    def match_tracks(self, itunes_tracklist):
        '''Returns a list of tuple pairs: (itunes_track, discogs_track)
        '''
        tracks = []
        for i_track in itunes_tracklist:
            d_track = self.utils.match_track(i_track, self.discogs_tracklist)
            tracks.append((i_track, d_track))
        return tracks

    def print_matches(self, matched):
        print ''
        for i in range(len(matched)):
            i_track, d_track = matched[i]
            print self.utils.pf(i_track, '%s i' % i)
            print self.utils.pf(d_track, '%s d' % i)
            print ''

    def write_info(self, matched):
        cont = raw_input('Press \'y\' to write track info, any key to abort: ').strip()
        if cont != 'y':
            print 'Aborted'
            return False
        else:
            print 'Writing...'

        for itunes_track, discogs_track in matched:
            self.utils.write(itunes_track, discogs_track)

        print 'Write complete'
        return True

    def start_tool(self):
        end = False
        while not end:
            sys.stdout.flush()
            itunes_tracklist = self.get_selected()
            sys.stdout.flush()
            matched = self.match_tracks(itunes_tracklist)
            sys.stdout.flush()
            self.print_matches(matched)
            end = self.write_info(matched)

        log.info('done... closing in 5 seconds...')
        time.sleep(5)


class Scanner(FixiTunesFromID):

    def __init__(self):
        self.utils = FixerUtilities()
        self.iTunes = connect_to_itunes()
        self.start_tool()

    def get_selected(self):
        itunes_tracklist = []
        while itunes_tracklist == []:
            raw_input('Select tracks in iTunes (any key to continue)')

            selected = self.iTunes.SelectedTracks
            if selected is not None:
                for track in selected:
                    itunes_tracklist.append(track)
            else:
                print 'Error: nothing selected in iTunes'

        return itunes_tracklist

    def group_itunes_tracklist_by_release(self, tracklist):
        releases = {}

        for track in tracklist:
            this_id = None

            if track.Grouping.startswith('D:'):
                this_id = int(track.Grouping[2:])

            if this_id: # track has an ID -- deal with it
                if this_id in releases.keys():
                    releases[this_id].append(track)
                else:
                    releases[this_id] = [track]
            else:
                print '%s has no associated Discogs ID' % track.Name

        return releases

    def fix(self):
        for release_id in self.itunes_releases:
            discogs = DiscogsTracklist(release_id)
            self.discogs_tracklist = discogs.get_release_info()
            self.itunes_tracklist = self.itunes_releases[release_id]
        return

    def start_tool(self):
        end = False
        while not end:
            self.itunes_releases = self.split_itunes_tracklist_by_release(self.get_selected())
            sys.stdout.flush()
            self.fix()
            sys.stdout.flush()
            self.matched = self.match_tracks()
            sys.stdout.flush()
            end = self.write_info()
        print "done"
        return


class FixerUtilities(object):

    def pf(self, track, id = ''):
        if track is None:
            return 'track is None'

        info = {'id': id,
                'name': track.Name,
                'artist': track.Artist,
                'tn': track.TrackNumber,
                'tc': track.TrackCount,
                'writers': track.Composer,
                'dn': track.DiscNumber,
                'dc': track.DiscCount}

        try:
            s = u"{id:>3} {tn:>3}/{tc:<2} {dn:>2}/{dc:<3} {name} - {artist} (writers: {writers})".format(**info)
        except:
            s = "{id:>3} {tn:>3}/{tc:<2} {dn:>2}/{dc:<3} Could not print details. Unicode data will be there, promise.".format(**info)
        return s

    def write(self, i, d): # i -> iTunes track, d -> Discogs track
        if d is None:
            log.error('Discogs track is None: did not write. iTunes track:')
            log.error(self.pf(i))
            return

        if d.Name is not None and i.Name != d.Name:
            i.Name = d.Name

        if d.Artist is not None and i.Artist != d.Artist:
            i.Artist = d.Artist
        '''
        if d.AlbumArtist is not None:
            i.AlbumArtist = d.AlbumArtist
        '''
        if d.Album is not None and i.Album != d.Album:
            i.Album = d.Album

        if d.Grouping is not None and i.Grouping != d.Grouping:
            i.Grouping = d.Grouping

        if d.Composer is not None and i.Composer != d.Composer:
            i.Composer = d.Composer

        if d.Comments is not None and i.Comment != d.Comments:
            i.Comment = d.Comments

        if d.Genre is not None and i.Genre != d.Genre:
            i.Genre = d.Genre

        if d.Year is not None and i.Year != d.Year:
            i.Year = d.Year

        if d.TrackNumber is not None and i.TrackNumber != d.TrackNumber:
            i.TrackNumber = d.TrackNumber

        if d.TrackCount is not None and i.TrackCount != d.TrackCount:
            i.TrackCount = d.TrackCount

        if d.DiscNumber is not None and i.DiscNumber != d.DiscNumber:
            i.DiscNumber = d.DiscNumber

        if d.DiscCount is not None and i.DiscCount != d.DiscCount:
            i.DiscCount = d.DiscCount

        return

    def match_track(self, itunes_track, discogs_tracklist):
        '''Consumes an iTunes track, and selects its best match from a Discogs
        tracklist. Removes that Discogs track from the list and returns it.
        '''
        i_str = '%s%s' % (itunes_track.Name, itunes_track.Artist)

        highest_index = -1
        highest_ratio = -1

        for index in range(len(discogs_tracklist)):
            d_track = discogs_tracklist[index]
            d_str = '%s%s' % (d_track.Name, d_track.Artist)

            ratio = difflib.SequenceMatcher(None, i_str.lower(), d_str.lower()).ratio()

            if ratio > highest_ratio:
                highest_ratio = ratio
                highest_index = index

        log.debug('this track')
        log.debug(self.pf(itunes_track))
        log.debug('\nd_tracklist')
        for track in discogs_tracklist:
            log.debug(self.pf(track))

        log.debug('highest_index %s' % highest_index)
        log.debug('highest_ratio %s' % highest_ratio)
        if highest_index > -1:
            log.debug('\nthis match')
            log.debug(self.pf(discogs_tracklist[highest_index]))
            return discogs_tracklist.pop(highest_index)
        else:
            log.debug('no match')


if __name__ == '__main__':
    fixer = FixiTunesFromID()
    #scanner = Scanner()
