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
import netaddr

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import workflows
from horizon.utils import fields

from openstack_dashboard import api


LOG = logging.getLogger(__name__)


class SetTemplateAction(workflows.Action):

    class Meta:
        name = ('Select Template')
        help_text = _('From here you can select a template to launch '
                      'a stack.')

    template_data = forms.CharField(
        widget=forms.HiddenInput(), required=False)
    stack_name = forms.CharField(
        max_length='255',
        label=_('Stack Name'),
        help_text=_('Name of the stack to create.'),
        required=True)
    template_upload = forms.FileField(
        label=_('Template File'),
        help_text=('A local template to upload.'),
        required=False)
    template_url = forms.URLField(
        label=_('Template Location'),
        help_text=_('An external (HTTP) URL to load the template from.'),
        verify_exists=True,
        required=False)
    enable_rollback = forms.BooleanField(
        label=_('Rollback on failure'),
        help_text=_('Enable rollback on create/update failure.'),
        required=False)
    timeout_mins = forms.IntegerField(
        initial=60,
        label=_('Creation Timeout'),
        help_text=_('Stack creation timeout in minutes.'),
        required=True)

    def clean(self):
        cleaned_data = super(SetTemplateAction, self).clean()
        template_url = cleaned_data.get('template_url')
        template_data = cleaned_data.get('template_data')
        files = self.request.FILES
        has_upload = 'template_upload' in files

        if has_upload and not template_url:
            del cleaned_data['template_url']
            tpl = self.request.FILES[
                'template_upload'].read()
            self.data['template_data'] = tpl
            if tpl.startswith('{'):
                cleaned_data['template_data'] = json.loads(tpl)
            else:
                cleaned_data['template_data'] = tpl
            template_name = self.request.FILES['template_upload'].name
            LOG.info('got upload %s' % template_name)

        elif template_url and not has_upload:
            del cleaned_data['template_data']
            del self.data['template_data']

        elif not template_data:
            msg = _('Select either a "Template File" or "Template Location"')
            raise forms.ValidationError(msg)

        #LOG.info('SetTemplateAction cleaned data %s' % cleaned_data)
        return cleaned_data


class SetParametersAction(workflows.Action):

    class Meta:
        name = ('Set Stack Parameters')
        help_text = _('Set the launch parameters for the selected template')

    def __init__(self, request, context, *args, **kwargs):
        super(SetParametersAction, self).__init__(request, context, *args, **kwargs)
        template_url = context.get('template_url')
        template_data = context.get('template_data')
        self.params_rendered = False
        if template_url:
            self.template_validate = api.heat.template_validate(
                request,
                template_url=template_url)
            self._build_parameters_form()
        elif template_data:
            self.template_validate = api.heat.template_validate(
                request,
                template=template_data)
            self._build_parameters_form()

    def clean(self):
        cleaned = super(SetParametersAction, self).clean()
        LOG.info('SetParametersAction cleaned data %s' % cleaned)
        params_submitted = cleaned.get('params_submitted')
        if self.params_rendered and not params_submitted:
            msg = _('Enter the launch parameters for this template')
            raise forms.ValidationError(msg)

        context = self.data
        LOG.info('LaunchStack handle context %s' % context)
        parameters = dict((k[8:], v) for (k, v) in cleaned.iteritems()
            if k.startswith('__param_'))
        fields = {
            'stack_name': context.get('stack_name'),
            'timeout_mins': context.get('timeout_mins'),
            'disable_rollback': not(context.get('enable_rollback')),
            'parameters': parameters}
        template_url = context.get('template_url')
        template_data = context.get('template_data')
        if template_url:
            fields['template_url'] = template_url
        elif template_data:
            fields['template'] = template_data

        LOG.info('SetParametersAction handle create fields %s' % fields)

        try:
            api.heat.stack_create(self.request, **fields)
        except Exception as e:
            raise forms.ValidationError(e)

        return cleaned

    def _build_parameters_form(self):

        self.params_rendered = True
        self.fields['params_submitted'] = forms.CharField(
            widget=forms.HiddenInput(attrs={'value': 'True'}), required=False)
        self.help_text = self.template_validate['Description']
        params = self.template_validate.get('Parameters', {})
        for param_key, param in params.items():
            field_key = '__param_%s' % param_key
            field_args = {
                'initial': param.get('DefaultValue', None),
                'label': param_key,
                'help_text': param.get('Description', ''),
                'required': False
            }
            param_type = param.get('Type', None)
            if 'AllowedValues' in param:
                choices = map(lambda x: (x, x), param['AllowedValues'])
                field_args['choices'] = choices
                self.fields[field_key] = forms.ChoiceField(**field_args)

            elif param_type in ('CommaDelimitedList', 'String'):
                if 'MinLength' in param:
                    field_args['min_length'] = int(param['MinLength'])
                if 'MaxLength' in param:
                    field_args['max_length'] = int(param['MaxLength'])
                field_args['required'] = param.get('MinLength', None) > 0
                self.fields[field_key] = forms.CharField(**field_args)

            elif param_type == 'Number':
                if 'MinValue' in param:
                    field_args['min_value'] = int(param['MinValue'])
                if 'MaxValue' in param:
                    field_args['max_value'] = int(param['MaxValue'])
                self.fields[field_key] = forms.IntegerField(**field_args)


class SetTemplate(workflows.Step):
    action_class = SetTemplateAction
    slug = 'select_template'
    contributes = ('template_url', 'template_data', 'stack_name',
                   'timeout_mins', 'enable_rollback')


class SetParameters(workflows.Step):
    action_class = SetParametersAction
    slug = 'set_params'

    @property
    def contributes(self):
        if not getattr(self, "_action", None):
            return ()
        field_keys = self.action.fields.keys()
        LOG.info('contributes %s' % field_keys)
        return field_keys

    @property
    def action(self):
        action = super(SetParameters, self).action
        if action.params_rendered:
            self.workflow.finalize_button_name = _('Launch')
        return action


class LaunchStack(workflows.Workflow):
    slug = 'launch_stack'
    name = _('Launch Stack')
    multipart = True
    finalize_button_name = _('Next')
    success_message = _('Launched stack named "%(name)s".')
    failure_message = _('Unable to launch stack named "%(name)s".')
    default_steps = (SetTemplate, SetParameters)

    def get_success_url(self):
        return reverse("horizon:project:stacks:index")

    def get_failure_url(self):
        return reverse("horizon:project:stacks:index")

    def format_status_message(self, message):
        name = self.context.get('name', 'unknown stack')
