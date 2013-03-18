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

import json
import logging

from horizon import tables
from horizon import forms
from horizon import messages
from horizon import tabs
from horizon import workflows

from django.core.urlresolvers import reverse_lazy
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.core.cache import cache
from django.views import generic

from openstack_dashboard import api

from .tables import StacksTable
from .forms import UploadTemplate
from .tabs import StackDetailTabs
from .tabs import ResourceDetailTabs
from .workflows import LaunchStack


LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    table_class = StacksTable
    template_name = 'project/stacks/index.html'

    def _inject_name(self, stack):
        # Horizon expects the object to have a name property
        # in order for the delete functionality to work properly
        # this function is mapped onto a stack object
        # setting the name property equal to the stack_name
        stack.name = stack.stack_name
        return stack

    def get_data(self):
        stacks = api.heat.stacks_list(self.request)
        stacks = map(self._inject_name, stacks)
        return stacks


class LaunchStackView(workflows.WorkflowView):
    workflow_class = LaunchStack
    template_name = "project/stacks/launch.html"

    def get_initial(self):
        initial = super(LaunchStackView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial


class DetailView(tabs.TabView):
    tab_group_class = StackDetailTabs
    template_name = 'project/stacks/detail.html'

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context["stack"] = self.get_data(self.request)
        return context

    def get_data(self, request, **kwargs):
        if not hasattr(self, "_stack"):
            stack_id = kwargs['stack_id']
            try:
                stack = api.heat.stack_get(request, stack_id)
                self._stack = stack
            except Exception, e:
                messages.error(request, e)
                redirect = reverse('horizon:project:stacks:index')
                return HttpResponseRedirect(redirect)
        return self._stack

    def get_tabs(self, request, **kwargs):
        stack = self.get_data(request, **kwargs)
        return self.tab_group_class(request, stack=stack, **kwargs)


class ResourceView(tabs.TabView):
    tab_group_class = ResourceDetailTabs
    template_name = 'project/stacks/resource.html'

    def get_context_data(self, **kwargs):
        context = super(ResourceView, self).get_context_data(**kwargs)
        context["resource"] = self.get_data(self.request, **kwargs)
        context["metadata"] = self.get_metadata(self.request, **kwargs)
        return context

    def get_data(self, request, **kwargs):
        if not hasattr(self, "_resource"):
            try:
                resource = api.heat.resource_get(
                    request,
                    kwargs['stack_id'],
                    kwargs['resource_name'])
                self._resource = resource
            except Exception, e:
                messages.error(request, e)
                redirect = reverse('horizon:project:stacks:index')
                return HttpResponseRedirect(redirect)
        return self._resource

    def get_metadata(self, request, **kwargs):
        if not hasattr(self, "_metadata"):
            try:
                metadata = api.heat.resource_metadata_get(
                    request,
                    kwargs['stack_id'],
                    kwargs['resource_name'])
                self._metadata = json.dumps(metadata, indent=2)
            except Exception, e:
                messages.error(request, e)
                redirect = reverse('horizon:project:stacks:index')
                return HttpResponseRedirect(redirect)
        return self._metadata

    def get_tabs(self, request, **kwargs):
        resource = self.get_data(request, **kwargs)
        metadata = self.get_metadata(request, **kwargs)
        return self.tab_group_class(
            request, resource=resource, metadata=metadata, **kwargs)
