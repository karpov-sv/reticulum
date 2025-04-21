from django.http import HttpResponse, FileResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.conf import settings

from django.contrib import messages

from django.contrib.auth.decorators import login_required

import os, io
import shutil

from . import models


def index(request):
    context = {}

    return TemplateResponse(request, 'index.html', context=context)
