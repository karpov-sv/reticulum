#!/usr/bin/env python3

import os, sys, glob
import io
from tqdm.auto import tqdm

import numpy as np
from astropy.table import Table
from astropy import units as u

from mocpy import MOC

from stdpipe.db import DB

if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser(usage="usage: %prog [options] args")
    parser.add_option('-d', '--db', help='Database name', action='store', dest='db', type='str', default='reticulum')
    parser.add_option('-H', '--host', help='Database host', action='store', dest='dbhost', type='str', default=None)
    parser.add_option('-v', '--verbose', help='Verbose', action='store_true', dest='verbose', default=False)

    (options,files) = parser.parse_args()

    if not len(files):
        sys.exit()

    db = DB(dbname=options.db, dbhost=options.dbhost)
    db.conn.autocommit = False
    cur = db.conn.cursor()

    s = io.StringIO()

    for i,filename in enumerate(tqdm(files)):
        dirname = os.path.split(filename)[0]
        obj = Table.read(filename)

        moc = MOC.from_lonlat(
            obj["ra"].T * u.deg,
            obj["dec"].T * u.deg,
            max_norder=10,
        )

        seq_id = db.query(
            'INSERT INTO sequences (path, site, observer, filter, target, moc) '
            'VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id',
            (
                dirname,
                obj.meta['Telescope'],
                obj.meta['Observer'],
                obj.meta['Filter'],
                obj.meta['Object'],
                moc.to_string(),
            ),
            table=False,
        )

        if not seq_id:
            # Sequence already exists
            res = db.query('SELECT id,moc FROM sequences WHERE path = %s', (dirname,), table=False, simplify=False)
            seq_id = int(res[0]['id'])
            moc0 = MOC.from_string(res[0]['moc'])
        else:
            moc0 = None

        frame_id = db.query(
            'INSERT INTO frames (sequence, time, filter, exposure, ra, dec, radius, pixscale, width, height, moc, keywords) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id',
            (
                seq_id,
                obj['time'][0].datetime,
                #obj['mag_filter_name'][0],
                obj.meta['Filter'],
                obj.meta['ExposureTime'],
                obj.meta['CenterRADeg'], obj.meta['CenterDecDeg'],
                0.5*np.hypot(
                    obj.meta['Width']*obj.meta['PixelScaleX'],
                    obj.meta['Depth']*obj.meta['PixelScaleY']
                )/3600,
                0.5*np.hypot(
                    obj.meta['PixelScaleX'],
                    obj.meta['PixelScaleY']
                )/3600,
                obj.meta['Width'],
                obj.meta['Depth'],
                moc.to_string(),
                obj.meta,
            ),
            table=False,
        )

        if frame_id:
            Table({
                'sequence':[seq_id]*len(obj), 'frame': [frame_id]*len(obj), 'time':obj['time'].datetime,
                'filter': obj['mag_filter_name'], 'ra': obj['ra'], 'dec': obj['dec'],
                'mag': obj['mag_calib'], 'magerr': obj['mag_calib_err'],
                'color_term': obj['mag_color_term'][:,0], 'color_term2': obj['mag_color_term'][:,1],
                'flags': obj['flags'], 'fwhm': obj['fwhm'],
            }).write(s, format='ascii.no_header', delimiter='\t')

            # Now update MOC of the sequence
            if moc0 is not None:
                moc0 = moc0.union(moc)
                db.query('UPDATE sequences SET moc = %s WHERE path = %s', (moc0.to_string(), dirname))

        columns = ['sequence', 'frame', 'time', 'filter', 'ra', 'dec', 'mag', 'magerr', 'color_term', 'color_term2', 'flags', 'fwhm']

        if i % 100 == 0 or i == len(files) - 1:
            s.seek(0)
            cur.copy_from(s, 'photometry', sep='\t', columns=columns, size=65535000)
            s = io.StringIO()

            db.conn.commit()
