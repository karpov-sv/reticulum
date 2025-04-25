from django.http import HttpResponse, FileResponse
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_protect, csrf_exempt, ensure_csrf_cookie
from django.db.models import Q
from django.urls import reverse
from django.contrib import messages

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import json

from urllib.parse import urlencode

from astropy.time import Time
from astropy.stats import mad_std

from stdpipe import resolve

from . import models
from . import forms
from . import utils


def radectoxieta(ra, dec, ra0=0, dec0=0):
    ra,dec = [np.asarray(_) for _ in (ra,dec)]
    delta_ra = np.asarray(ra - ra0)

    delta_ra[(ra < 10) & (ra0 > 350)] += 360
    delta_ra[(ra > 350) & (ra0 < 10)] -= 360

    xx = np.cos(dec*np.pi/180)*np.sin(delta_ra*np.pi/180)
    yy = np.sin(dec0*np.pi/180)*np.sin(dec*np.pi/180) + np.cos(dec0*np.pi/180)*np.cos(dec*np.pi/180)*np.cos(delta_ra*np.pi/180)
    xi = (xx/yy)

    xx = np.cos(dec0*np.pi/180)*np.sin(dec*np.pi/180) - np.sin(dec0*np.pi/180)*np.cos(dec*np.pi/180)*np.cos(delta_ra*np.pi/180)
    eta = (xx/yy)

    xi *= 180./np.pi
    eta *= 180./np.pi

    return xi,eta


def get_lc(request):
    lc = models.Photometry.objects.order_by('time')

    magerr = request.GET.get('magerr')
    if magerr:
        magerr = float(magerr)
        lc = lc.filter(magerr__lt=magerr)

    ra = float(request.GET.get('ra'))
    dec = float(request.GET.get('dec'))
    sr = float(request.GET.get('sr', 0.01))

    # Lc with centers within given search radius
    lc = lc.extra(where=["q3c_radial_query(ra, dec, %s, %s, %s)"], params=(ra, dec, sr/3600))

    return lc


from scipy.optimize import minimize

def get_bv(mags, magerrs, fnames, color_terms, color_terms2):
    def fn(bvs):
        results = []

        for bv in bvs:
            value = 0
            for fn in np.unique(fnames):
                idx = fnames == fn
                idx &= np.isfinite(mags)
                mag = mags[idx]
                magerr = magerrs[idx]
                mag += color_terms[idx]*bv + color_terms2[idx]*bv**2

                value += np.sum((mag - np.mean(mag))**2 / magerr**2)

            results.append(np.sqrt(value))

        return results

    res = minimize(fn, [1.0], tol=1e-12)

    return res['x'][0]

@csrf_exempt
def lc(request, mode="jpg", size=800):
    lc = get_lc(request)

    times = np.array([_.time for _ in lc])
    filters = np.array([_.filter for _ in lc])
    ras = np.array([_.ra for _ in lc])
    decs = np.array([_.dec for _ in lc])
    mags = np.array([_.mag for _ in lc])
    magerrs = np.array([_.magerr for _ in lc])
    flags = np.array([_.flags for _ in lc])
    fwhms = np.array([_.fwhm for _ in lc])
    color_terms = np.array([_.color_term for _ in lc])
    color_terms2 = np.array([_.color_term2 for _ in lc])

    mjds = Time(times).mjd if len(times) else []

    bv = get_bv(mags, magerrs, filters, color_terms, color_terms2)

    mags += color_terms * bv
    mags += color_terms2 * bv**2

    cols = np.array([{
        'Bmag':'blue',
        'Vmag':'green',
        'Rmag':'red',
        'Imag':'orange',
        'gmag':'green',
        'rmag':'red',
        'imag':'orange',
        'zmag':'magenta',
    }.get(_, 'black') for _ in filters])

    ra = float(request.GET.get('ra'))
    dec = float(request.GET.get('dec'))
    sr = float(request.GET.get('sr', 1/3600))
    name = request.GET.get('name')

    if name in ['sexadecimal', 'degrees']:
        name = None

    # Quality cuts
    idx0 = np.isfinite(mags)

    context = {}

    context['ra'] = float(ra)
    context['dec'] = float(dec)
    context['sr'] = float(sr)

    if name:
        title = '%s  :  ' % name
    else:
        title = ''

    title += '%.4f %.3f %.1f"  :  %d pts  :  B-V = %.2f' % (ra, dec, sr, len(mags), bv)

    xi,eta = radectoxieta(ras, decs, ra, dec)
    xi *= 3600
    eta *= 3600

    if mode == 'jpeg':
        # Plot lc
        fig = Figure(facecolor='white', dpi=72, figsize=(size/72,0.5*size/72), tight_layout=True)
        ax = fig.add_subplot(111)
        ax.grid(True, alpha=0.1, color='gray')

        for fn in np.unique(filters):
            idx = idx0 & (filters == fn)

            if len(mags[idx]) < 2:
                continue

            ax.errorbar(times[idx], mags[idx], magerrs[idx], fmt='.', color=cols[idx][0], capsize=0, alpha=0.3)
            ax.scatter(times[idx], mags[idx], marker='.', c=cols[idx][0])
            ax.invert_yaxis()

        ax.invert_yaxis()

        ax.set_title(title)

        canvas = FigureCanvas(fig)

        response = HttpResponse(content_type='image/jpeg')
        canvas.print_jpg(response)

        return response

    elif mode == 'json':
        lcs = []

        for fn in np.unique(filters):
            idx = idx0 & (filters == fn)

            if len(mags[idx]) < 2:
                continue

            times_idx = [_.isoformat() for _ in times[idx]]

            lcs.append({'filter': fn, 'color': cols[idx][0],
                        'time': times_idx, 'mjd': list(mjds[idx]), 'xi': list(xi[idx]), 'eta': list(eta[idx]),
                        'mag': list(mags[idx]), 'magerr': list(magerrs[idx]), 'flags': list(flags[idx]),
                        'fwhm': list(fwhms[idx]), 'color_term': list(color_terms[idx]), 'color_term2': list(color_terms2[idx])})

        data = {'name': name, 'title': title, 'ra': ra, 'dec': dec, 'sr': sr, 'bv': bv, 'lcs': lcs}

        return HttpResponse(json.dumps(data, cls=utils.NumpyEncoder), content_type="application/json")

    elif mode == 'text':
        response = HttpResponse(request, content_type='text/plain')

        response['Content-Disposition'] = 'attachment; filename=lc_full_%s_%s_%s.txt' % (ra, dec, sr)

        print('# Date Time MJD Site CCD Filter Mag Magerr Flags FWHM Std Nstars', file=response)

        for _ in xrange(len(times)):
            print(times[_], mjds[_], sites[_], ccds[_], filters[_], mags[_], magerrs[_], flags[_], fwhms[_], stds[_], nstars[_], file=response)

        return response

    elif mode == 'mjd':
        response = HttpResponse(request, content_type='text/plain')

        response['Content-Disposition'] = 'attachment; filename=lc_mjd_%s_%s_%s.txt' % (ra, dec, sr)

        if len(np.unique(filters)) == 1:
            single = True
        else:
            single = False

        if single:
            print('# MJD Mag Magerr', file=response)
        else:
            print('# MJD Mag Magerr Filter', file=response)

        idx = idx0

        for _ in xrange(len(times[idx])):
            if single:
                print(mjds[idx][_], mags[idx][_], magerrs[idx][_], file=response)
            else:
                print(mjds[idx][_], mags[idx][_], magerrs[idx][_], filters[idx][_], file=response)

        return response


def photometry(request):
    context = {}

    form = forms.PhotometryForm(request.POST or None)

    context = {'form': form}

    if request.method == 'POST':
        # Form submission handling
        if form.is_valid():
            target_name = form.cleaned_data.get('target')
            sr = form.cleaned_data.get('sr')

            target = resolve.resolve(target_name)

            if target is None:
                messages.warning(request, f"Cannot resolve target: {target_name}")
            else:
                messages.success(request, f"Resolved to: {target.ra.deg:.4f} {target.dec.deg:.4f}")

                context['target_name'] = target_name
                context['target'] = target
                context['sr'] = sr

                params = {
                    'name': target_name,
                    'ra': target.ra.deg,
                    'dec': target.dec.deg,
                    'sr': sr,
                }

                context['lc_json'] = reverse('photometry_json') + '?' + urlencode(params)


    return TemplateResponse(request, 'photometry.html', context=context)
