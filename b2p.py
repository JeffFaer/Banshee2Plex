#!/usr/bin/env python

import argparse
import logging
import mimetypes
import os
import urllib
import sqlite3
import sys

class B2P:
    def __init__(self):
        parser = argparse.ArgumentParser(description='Import banshee data into Plex')
        parser.add_argument('--banshee-db', dest='banshee_db', action='store', default=os.path.join(os.getenv('HOME'), '.config', 'banshee-1', 'banshee.db'), help='path to banshee DB')
        parser.add_argument('--plex-db', dest='plex_db', action='store', default=os.path.join(os.path.abspath(os.path.sep), 'var', 'lib', 'plexmediaserver', 'Library', 'Application Support', 'Plex Media Server', 'Plug-in Support', 'Databases', 'com.plexapp.plugins.library.db'), help='path to plex DB')
        parser.add_argument('--plex-account', dest='plex_account', action='store', required=True, help='The email address of the plex user to add ratings for.')
        parser.add_argument('--update-ratings', dest='update_ratings', action='store_true')
        parser.add_argument('--dry-run', dest='dry_run', action='store_true')

        self.args = parser.parse_args()

        if not os.path.isfile(self.args.banshee_db):
            raise ValueError("Cannot find banshee db at %s" % self.args.banshee_db)
        if not os.path.isfile(self.args.plex_db):
            raise ValueError("Cannot find plex db at %s" % self.args.plex_db)

        self.banshee = sqlite3.connect(self.args.banshee_db, timeout=5.0, detect_types=sqlite3.PARSE_DECLTYPES)
        self.banshee.isolation_level = None
        self.banshee.text_factory = str
        self.banshee.row_factory = sqlite3.Row

        self.plex = sqlite3.connect(self.args.plex_db, timeout=5.0, detect_types=sqlite3.PARSE_DECLTYPES)
        self.plex.isolation_level = None
        self.plex.text_factory = str
        self.plex.row_factory = sqlite3.Row

        logging.basicConfig(file=sys.stderr, level=logging.INFO, format='%(asctime)-15s [+] %(levelname)s %(message)s')

        self._get_plex_account_id()

    def _get_plex_account_id(self):
        cursor = self.plex.cursor()

        query = 'SELECT id FROM accounts WHERE name = :name;'
        cursor.execute(query, {'name': self.args.plex_account})

        row = cursor.fetchone()
        if not row:
            raise ValueError('Could not find user %s in plex', self.args.plex_account)

        return row['id']


    def run(self):
        ban_cursor = self.banshee.cursor()

        if self.args.update_ratings:
            logging.info('Updating ratings from banshee...')

            query = 'SELECT uri, rating FROM CoreTracks;'
            ban_cursor.execute(query)

            n = 0
            for item in ban_cursor:
                if item['uri'] is None:
                    logging.warn('uri is None: %s', item)
                path = to_path(item['uri'])
                if not os.path.isfile(path):
                    logging.warn('could not find %s', path)
                    continue
                if not is_audio_file(path):
                    logging.warn('path is not audio %s', path)
                    continue

                plex_id = self._get_plex_metadata_item_guid(path)
                # banshee ratings are [0, 5], but plex expects [0.0, 10.0]
                self._update_plex_metadata(path, plex_id, item['rating'] * 2.0)

                n += 1

            logging.info('Checked %d files', n)

    def _get_plex_metadata_item_guid(self, path):
        cursor = self.plex.cursor()

        query = 'SELECT media_item_id FROM media_parts WHERE file = :file;'
        cursor.execute(query, {'file': path})

        row = cursor.fetchone()
        if not row:
            raise ValueError('Cannot find "%s" in plex' % path)

        media_item_id = row['media_item_id']
        query = 'SELECT metadata_item_id FROM media_items WHERE id = :id;'
        cursor.execute(query, {'id': media_item_id})

        row = cursor.fetchone()
        if not row:
            raise ValueError('Cannot find metadata_item_id for "%s" (ID %s) in plex' % (path, media_item_id))

        metadata_item_id = row['metadata_item_id']
        query = 'SELECT guid FROM metadata_items WHERE id = :id;'
        cursor.execute(query, {'id': metadata_item_id})

        row = cursor.fetchone()
        if not row:
            raise ValueError('Cannot find guid for "%s (ID %s, %s) in plex' % (path, media_item_id, metadata_item_id))

        return row['guid']

    def _update_plex_metadata(self, path, plex_guid, rating):
        account_id = self._get_plex_account_id()

        cursor = self.plex.cursor()

        query = 'SELECT id FROM metadata_item_settings WHERE guid = :guid AND account_id = :account_id;'
        cursor.execute(query, {'guid': plex_guid, 'account_id': account_id})

        row = cursor.fetchone()
        if row:
            query = """
            UPDATE
                metadata_item_settings
            SET
                rating = :rating
            WHERE
                id = :id
                AND account_id = :account_id
                AND (rating != :rating)
            ;
            """
            args = {
                    'id': row['id'],
                    'account_id': account_id,
                    'rating': rating,
                    }
        else:
            query = """
            INSERT INTO
                metadata_item_settings
                (account_id, guid, rating)
            VALUES
                (:account_id, :guid, :rating)
            ;
            """
            args = {
                    'account_id': account_id,
                    'guid': plex_guid,
                    'rating': rating,
                    }
        if self.args.dry_run:
            logging.info("Would execute %s\n%s", query, args)
        else:
            cursor.execute(query, args)
            if cursor.rowcount != 0:
                logging.info("%s rating updated to %s", path, rating)


def to_path(uri):
    uri = urllib.unquote(uri)
    if uri.startswith('file:///'):
        uri = uri[7:]
    return uri

def is_audio_file(path):
    return mimetypes.guess_type(path)[0].split('/')[0] == 'audio'

if __name__ == '__main__':
    b2p = B2P()
    b2p.run()

sys.exit(1)
