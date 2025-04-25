import numpy as np

from stdpipe import astrometry, photometry, catalogs, cutouts, templates, subtraction, plots, pipeline, utils, psf

from astropy.table import Table, vstack
from astropy.stats import mad_std
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.time import Time


# Supported filters and their aliases
supported_filters = {
    # Johnson-Cousins
    'U': {'name':'Johnson-Cousins U', 'aliases':[]},
    'B': {'name':'Johnson-Cousins B', 'aliases':[]},
    'V': {'name':'Johnson-Cousins V', 'aliases':[]},
    'R': {'name':'Johnson-Cousins R', 'aliases':["Rc"]},
    'I': {'name':'Johnson-Cousins I', 'aliases':["Ic", "I'"]},
    # Sloan-like
    'u': {'name':'Sloan u', 'aliases':["sdssu", "SDSS u", "SDSS-u", "SDSS-u'", "Sloan-u", "sloanu", "Sloan u", "SloanU", "Su", "SU", "sU"]},
    'g': {'name':'Sloan g', 'aliases':["sdssg", "SDSS g", "SDSS-g", "SDSS-g'", "Sloan-g", "sloang", "Sloan g", "SloanG", "Sg", "SG", "sG", "ZTF_g"]},
    'r': {'name':'Sloan r', 'aliases':["sdssr", "SDSS r", "SDSS-r", "SDSS-r'", "Sloan-r", "sloanr", "Sloan r", "SloanR", "Sr", "SR", "sR", "ZTF_r"]},
    'i': {'name':'Sloan i', 'aliases':["sdssi", "SDSS i", "SDSS-i", "SDSS-i'", "Sloan-i", "sloani", "Sloan i", "SloanI", "Si", "SI", "sI", "ZTF_i"]},
    'z': {'name':'Sloan z', 'aliases':["sdssz", "SDSS z", "SDSS-z", "SDSS-z'", "Sloan-z", "sloanz", "Sloan z", "SloanZ", "Sz", "SZ", "sZ"]},
    # Gaia
    'G': {'name':'Gaia G', 'aliases':[]},
    'BP': {'name':'Gaia BP', 'aliases':[]},
    'RP': {'name':'Gaia RP', 'aliases':[]},
}

supported_catalogs = {
    'gaiadr3syn': {'name':'Gaia DR3 synphot', 'filters':['U', 'B', 'V', 'R', 'I', 'u', 'g', 'r', 'i', 'z', 'y'],
                   'limit': 'rmag'},
    'ps1': {'name':'Pan-STARRS DR1', 'filters':['B', 'V', 'R', 'I', 'g', 'r', 'i', 'z'],
            'limit':'rmag'},
    'skymapper': {'name':'SkyMapper DR4', 'filters':['B', 'V', 'R', 'I', 'g', 'r', 'i', 'z'],
                  'limit':'rPSF'},
    'sdss': {'name':'SDSS DR16', 'filters':['u', 'g', 'r', 'i', 'z'],
             'limit':'rmag'},
    'atlas': {'name':'ATLAS-REFCAT2', 'filters':['B', 'V', 'R', 'I', 'g', 'r', 'i', 'z'],
              'limit':'rmag'},
    'gaiaedr3': {'name':'Gaia eDR3', 'filters':['G', 'BP', 'RP'],
              'limit':'Gmag'},
}


def guess_catalogue_mag_columns(fname, cat):
    cat_col_mag = None
    cat_col_mag_err = None

    # Most of augmented catalogues
    if f"{fname}mag" in cat.colnames:
        cat_col_mag = f"{fname}mag"

        if f"e_{fname}mag" in cat.colnames:
            cat_col_mag_err = f"e_{fname}mag"

    # Non-augmented PS1 etc
    elif "gmag" in cat.colnames and "rmag" in cat.colnames:
        if fname in ['U', 'B', 'V', 'BP']:
            cat_col_mag = "gmag"
        if fname in ['R', 'G']:
            cat_col_mag = "rmag"
        if fname in ['I', 'RP']:
            cat_col_mag = "imag"

        if f"e_{cat_col_mag}" in cat.colnames:
            cat_col_mag_err = f"e_{cat_col_mag}"

    # SkyMapper
    elif f"{fname}PSF" in cat.colnames:
        cat_col_mag = f"{fname}PSF"

        if f"e_{fname}PSF" in cat.colnames:
            cat_col_mag_err = f"e_{fname}PSF"

    # Gaia DR2/eDR3/DR3 from Vizier
    elif "BPmag" in cat.colnames and "RPmag" in cat.colnames and "Gmag" in cat.colnames:
        if fname in ['U', 'B', 'V', 'R', 'u', 'g', 'r', 'BP']:
            cat_col_mag = "BPmag"
        elif fname in ['I', 'i', 'z', 'RP']:
            cat_col_mag = "RPmag"
        else:
            cat_col_mag = "Gmag"

        if f"e_{cat_col_mag}" in cat.colnames:
            cat_col_mag_err = f"e_{cat_col_mag}"

    # Gaia DR2/eDR3/DR3 from XMatch
    elif "phot_bp_mean_mag" in cat.colnames and "phot_rp_mean_mag" in cat.colnames and "phot_g_mean_mag" in cat.colnames:
        if fname in ['U', 'B', 'V', 'R', 'u', 'g', 'r', 'BP']:
            cat_col_mag = "phot_bp_mean_mag"
        elif fname in ['I', 'i', 'z', 'RP']:
            cat_col_mag = "phot_rp_mean_mag"
        else:
            cat_col_mag = "phot_g_mean_mag"

        if f"{cat_col_mag}_error" in cat.colnames:
            cat_col_mag_err = f"{cat_col_mag}_error"

    # else:
    #     raise RuntimeError(f"Unsupported filter {fname} and/or catalogue")

    return cat_col_mag, cat_col_mag_err


from astropy_healpix import healpy

def round_coords_to_grid(ra0, dec0, sr0, nside=None):
    """Tries to round the coordinates to nearest HEALPix pixel center"""
    if nside is None:
        for n in range(1, 16):
            nside = 2**n
            res = healpy.nside_to_pixel_resolution(nside).to('deg').value
            if res < 0.05*sr0:
                break
    else:
        res = healpy.nside_to_pixel_resolution(nside).to('deg').value

    ipix = healpy.ang2pix(nside, ra0, dec0, lonlat=True)
    ra1,dec1 = healpy.pix2ang(nside, ipix, lonlat=True)
    sr1 = (np.floor(sr0/res) + 1)*res

    return ra1, dec1, sr1
