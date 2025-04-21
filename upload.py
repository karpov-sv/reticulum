#!/usr/bin/env python3

import os, sys, glob
import io
from tqdm.auto import tqdm

import numpy as np
from astropy.table import Table

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
        obj = Table.read(filename)

        seq_id = 0

        frame_id = db.query(
            'INSERT INTO frames (sequence, time, filter, exposure, ra, dec, radius, pixscale, width, height) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id',
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
            ),
            table=False,
        )

        # for row in obj:
        #     print(
        #         seq_id, frame_id, row['time'].datetime,
        #         row['mag_filter_name'], row['ra'], row['dec'],
        #         row['mag_calib'], row['mag_calib_err'],
        #         row['mag_color_term'][0], row['mag_color_term'][1],
        #         row['flags'], row['fwhm'],
        #         sep='\t', end='\n', file=s
        #     )

        Table({
            'sequence':[seq_id]*len(obj), 'frame': [frame_id]*len(obj), 'time':obj['time'].datetime,
            'filter': obj['mag_filter_name'], 'ra': obj['ra'], 'dec': obj['dec'],
            'mag': obj['mag_calib'], 'magerr': obj['mag_calib_err'],
            'color_term': obj['mag_color_term'][:,0], 'color_term2': obj['mag_color_term'][:,1],
            'flags': obj['flags'], 'fwhm': obj['fwhm'],
        }).write(s, format='ascii.no_header', delimiter='\t')

        columns = ['sequence', 'frame', 'time', 'filter', 'ra', 'dec', 'mag', 'magerr', 'color_term', 'color_term2', 'flags', 'fwhm']

        if i % 100 == 0 or i == len(files) - 1:
            s.seek(0)
            cur.copy_from(s, 'photometry', sep='\t', columns=columns, size=65535000)
            s = io.StringIO()

            db.conn.commit()
