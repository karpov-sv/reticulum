from django.http import HttpResponse, FileResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.conf import settings

from django.contrib import messages

from django.contrib.auth.decorators import login_required

import os, io
import shutil

from mocpy import MOC

from . import models


def index(request):
    context = {}

    return TemplateResponse(request, 'index.html', context=context)


def coverage(request, seq_id=None, frame_id=None):
    moc0 = None

    for seq in models.Sequences.objects.all():
        moc = MOC.from_string(seq.moc)

        if moc0 is None:
            moc0 = moc
        else:
            moc0 = moc0.union(moc)

    if moc0 is not None:
        s = io.BytesIO()
        hdus = moc0.serialize(format='fits')
        hdus.writeto(s)

        response = HttpResponse(s.getvalue(), content_type='application/octet-stream')
        # response['Content-Disposition'] = 'attachment; filename=' + os.path.split(filename)[-1] + '.processed.fits'
        response['Content-Length'] = len(s.getvalue())
        return response

    return HttpResponse('coverage', content_type='text/plain')
