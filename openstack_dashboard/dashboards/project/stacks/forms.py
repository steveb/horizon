# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import httplib2
import logging

from horizon import messages
from horizon import forms

from django.core.cache import cache


LOG = logging.getLogger(__name__)


class UploadTemplate(forms.SelfHandlingForm):
    upload_template = forms.FileField(required=False)
    http_url = forms.CharField(required=False)

    def handle(self, request, data):
        if 'upload_template' in request.FILES:
            # local file upload
            template = request.FILES['upload_template'].read()
            template_name = request.FILES['upload_template'].name
            LOG.info('got upload %s' % template_name)
        elif 'http_url' in request.POST and request.POST['http_url']:
            # download from a given url
            url = request.POST['http_url']
            template_name = url.split('/')[-1]
            # TODO: make cache dir configurable via django settings
            # TODO: make disabling ssl verification configurable too
            h = httplib2.Http(".cache",
                              disable_ssl_certificate_validation=True)
            resp, template = h.request(url, "GET")
            if resp.status not in (200, 304):
                messages.error(request, 'URL returned status %s' % resp.status)
                return False
        else:
            # neither file or url were given
            messages.error(request, "Please choose a file or provide a url")
            return False

        # store the template so we can render it next
        cache.set('heat_template_' + request.user.username, template)
        cache.set('heat_template_name_' + request.user.username, template_name)
        # No template validation is done here, We'll let heat do that for us
        return True
