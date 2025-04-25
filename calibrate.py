#!/usr/bin/env python3

import os, sys, glob
import io
from tqdm.auto import tqdm

import numpy as np
from astropy.table import Table
from astropy.time import Time

from stdpipe import photometry, catalogs, pipeline

import reticulum
from reticulum import calibration


def process_frame(filename, verbose=False, reprocess=False):
    # Simple wrapper around print for logging in verbose mode only
    log = (verbose if callable(verbose) else print) if verbose else lambda *args,**kwargs: None

    outname = filename + '.parquet'

    if os.path.exists(outname) and not reprocess:
        return

    log(f"Processing {filename}")

    config = {}

    obj = reticulum.io.read_sips(filename, filled=True)

    if np.any(np.isnan(obj['ra'])):
        log("No sky coordinates, skipping")
        return

    time = Time(obj.meta['Exposure'])

    # Filter
    config['filter'] = obj.meta['Filter']
    # Normalize filters
    for fname in calibration.supported_filters.keys():
        if config['filter'] in calibration.supported_filters[fname]['aliases']:
            config['filter'] = fname
            log(f"Filter name normalized to {config['filter']}")
            break

    # Fallback filter
    if config['filter'] not in calibration.supported_filters.keys():
        log(f"Unknown filter {config['filter']}, falling back to r")
        config['filter'] = 'r'

    config['cat_name'] = 'gaiadr3syn'

    #
    pixscale = np.hypot(obj.meta['PixelScaleX'], obj.meta['PixelScaleY'])/3600
    obj['fwhm'] = np.hypot(obj['FWHMX'], obj['FWHMY'])
    fwhm = np.nanmedian(obj['fwhm'])
    log('FWHM', fwhm)

    aper = f"Ap{min(10, np.ceil(fwhm)):.0f}"
    log('Using aperture', aper)

    flux,fluxerr = obj[aper], obj[aper + 'Dev']
    obj['mag'] = -2.5*np.log10(flux)
    obj['magerr'] = 2.5 / np.log(10) * fluxerr / flux
    obj['flags'] = 0
    obj['flags'][~np.isfinite(obj['mag'])] = 32 # Saturated

    # Catalogue
    ra0, dec0 = obj.meta['CenterRADeg'], obj.meta['CenterDecDeg']
    sr0 = np.hypot(obj.meta['Width'], 1.1 * obj.meta['Depth']) * obj.meta['PixelScaleX'] / 2 / 3600
    ra00,dec00,sr00 = calibration.round_coords_to_grid(ra0, dec0, sr0)
    cat = catalogs.get_cat_vizier(
        ra00,
        dec00,
        sr00,
        config['cat_name'],
        filters={'rmag': '<16'},
        verbose=verbose,
    )

    # Catalogue settings
    config['cat_col_mag'],config['cat_col_mag_err'] = calibration.guess_catalogue_mag_columns(
        config['filter'],
        cat
    )

    if config['cat_col_mag'] in ['Umag', 'Bmag', 'Vmag', 'Rmag', 'Imag'] or True:
        config['cat_col_color_mag1'] = 'Bmag'
        config['cat_col_color_mag2'] = 'Vmag'
    elif config['cat_col_mag'] in ['umag', 'gmag', 'rmag', 'imag']:
        config['cat_col_color_mag1'] = 'gmag'
        config['cat_col_color_mag2'] = 'rmag'
    elif config['cat_col_mag'] in ['zmag']:
        config['cat_col_color_mag1'] = 'rmag'
        config['cat_col_color_mag2'] = 'imag'
    elif config['cat_col_mag'] in ['Gmag', 'BPmag', 'RPmag']:
        config['cat_col_color_mag1'] = 'BPmag'
        config['cat_col_color_mag2'] = 'RPmag'
    else:
        raise RuntimeError(f"Cannot guess magnitude columns for {config.get('cat_name')} and filter {config.get('filter')}")

    log(f"Will use catalogue column {config['cat_col_mag']} as primary magnitude ")
    log(f"Will use catalogue columns {config['cat_col_color_mag1']} and {config['cat_col_color_mag2']} for color")


    m = pipeline.calibrate_photometry(
        obj, cat, 2/3600,
        cat_col_mag=config.get('cat_col_mag'),
        cat_col_mag_err=config.get('cat_col_mag_err'),
        cat_col_mag1=config.get('cat_col_color_mag1'),
        cat_col_mag2=config.get('cat_col_color_mag2'),
        order=2,
        use_color=2,
        verbose=verbose, max_intrinsic_rms=0.02,
        nonlin=True,
    )

    obj['time'] = time
    obj['mjd'] = time.mjd

    obj['mag_filter_name'] = m['cat_col_mag']

    if 'cat_col_mag1' in m.keys() and 'cat_col_mag2' in m.keys():
        obj['mag_color_name'] = '%s - %s' % (m['cat_col_mag1'], m['cat_col_mag2'])
    if m['color_term'] is not None:
        obj['mag_color_term'] = [m['color_term']]*len(obj)

    obj.write(outname, overwrite=True)

    log(f"Calibrated measurements written to {outname}")


if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser(usage="usage: %prog [options] args")
    parser.add_option('-r', '--reprocess', help='Reprocess already processed frames', action='store_true', dest='reprocess', default=False)
    parser.add_option('-v', '--verbose', help='Verbose', action='store_true', dest='verbose', default=False)

    (options,files) = parser.parse_args()

    if options.verbose:
        progress_fn = tqdm
    else:
        progress_fn = lambda _: _

    for filename in progress_fn(files):
        process_frame(filename, verbose=options.verbose, reprocess=options.reprocess)
