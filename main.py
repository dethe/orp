#!/usr/bin/env python

import wsgiref.handlers
import logging

from google.appengine.ext import webapp
from models import *
from google.appengine.ext.webapp import template
from django.utils import simplejson
from google.appengine.api import users


def must_be_logged_in(fn):
    def logged_in_version(self, *args, **kws):
        if users.get_current_user():
            fn(self, *args, **kws)
        else:
            self.redirect('/')
    return logged_in_version

def dispatch_by_content_type(fn):
    fn_name = fn.__name__
    def dispatch(self, *args, **kws):
        fn(self, *args, **kws) # call original method for any setup
        fn_type = 'text'
        if 'text/html' in self.request.headers['Accept']:
            fn_type = 'html'
        elif 'text/json' in self.request.headers['Accept']:
            fn_type = 'json'
        return getattr(self, '%s_%s' % (fn_name, fn_type))(*args, **kws)
    return dispatch
    
class LCHandler(webapp.RequestHandler):
    
    def context(self):
        ctx = {}
        ctx['auth_url'], ctx['auth_text'] = self.auth_info()
        for key in 'request response model model_id message sketches sketch_name sketch_id objects members responsibilites partners potential_partners'.split():
            if hasattr(self, key):
                ctx[key] = getattr(self, key)
        ctx['handler'] = self
        ctx['success_url'] = self.success_url
        return ctx
    
    def render(self, body_template=None, context=None):
        if body_template is None:
            body_template = self.default_template
        if context is None:
            context = self.context()
        context['body_template'] = '%s.html' % body_template
        self.response.out.write(template.render('templates/layout.html', context))
        
    def auth_info(self):
        if users.get_current_user():
            url = users.create_logout_url('/')
            return url, 'logout'
        else:
            url = users.create_login_url('/')
            return url, 'login'
    
class MainHandler(LCHandler):
    
    default_template = 'main'
    
    success_url = '/'
    
    def get(self):
        if users.get_current_user():
            self.sketches = SketchModel.gql("WHERE owner = :1", users.get_current_user())
        self.render()
        
    def post(self):
        if self.request.get('object_type') == 'sketch':
            name = self.request.get('sketch')
            self.model = SketchModel(name=name)
            self.model.objects = []
            self.model.members = []
            self.model.owner = users.get_current_user()
            self.model.put()
            self.model_id = self.model.key().id()
            self.message = 'New sketch added successfully'
            self.redirect('/%d' % self.model.key().id())
        else:
            self.message = 'There was a problem adding the sketch'
            self.render()
        
    
class SketchHandler(LCHandler):
    
    default_template = 'sketch'
    
    @property
    def success_url(self):
        return '/%d' % int(self.model_id)
    
    @dispatch_by_content_type
    def get(self, sketch_id):
        self.model_id = sketch_id
        try:
            self.model = SketchModel.get_by_id(int(sketch_id))
            self.objects = ObjectModel.get(self.model.objects)
        except ValueError:
            self.model = SketchModel(name=sketch_id)
        
    def get_html(self, sketch_id):
        self.render()
        
    def get_json(self, sketch_id):
        self.response.out.write(template.render('templates/model.json', self.context()))
        
    def get_text(self, sketch_id):
        self.response.out.write('Model Handler for %s' % sketch_id)
        self.response.out.write('Accept: %s' % self.request.headers['Accept'])
            
    @must_be_logged_in
    @dispatch_by_content_type
    def post(self, sketch_id):
        pass
        
    def post_html(self, sketch_id):
        self.model_id = sketch_id
        if self.request.get('object_type') == 'object':
            self.model = SketchModel.get_by_id(int(sketch_id))
            self.model_id = sketch_id
            return self.post_html_object()
            
    def post_html_object(self):
        logging.debug('Request sends id for object: %s' % self.request.get('object'))
        if 'add' in self.request.arguments():
            the_object = ObjectModel(name=self.request.get('object'), parent=self.model)
            the_object.responsibilities = []
            the_object.partners = []
            the_object.put()
            self.model.objects.append(the_object.key())
        elif 'remove' in self.request.arguments():
            the_object = ObjectModel.get_by_id(int(self.request.get('object_id')))
            self.model.objects.remove(the_object.key())
            the_object.delete()
            
        self.model.put()
        self.redirect(self.success_url)
        
    def post_json(self, sketch_id):
        pass
        
class ObjectHandler(LCHandler):

    default_template = 'object'
    
    @property
    def success_url(self):
        return '/%d/%d' % (int(self.sketch_id), int(self.model_id))
        
    @dispatch_by_content_type
    def get(self, sketch_id, object_id):
        sketch = SketchModel.get_by_id(int(sketch_id))
        self.sketch_id = sketch_id
        self.sketch_name = sketch.name
        self.model_id = object_id
        self.model = ObjectModel.get_by_id(int(object_id), parent=sketch)
        self.potential_partners = ObjectModel.get(sketch.objects)
        self.partners = ObjectModel.get(self.model.partners)
    
    def get_html(self, sketch_id, object_id):
        self.render()
        
    def get_json(self, sketch_id, object_id):
        self.response.out.write(template.render('templates/client.json', {'model': sketch_id, 'client': object_id, 'request': self.request}))
        
    def get_text(self, sketch_id, object_id):
        self.response.out.write('Client Handler for client %s of model %s' % (object_id, sketch_id))
        
    @dispatch_by_content_type
    def post(self, sketch_id, object_id):
        pass
        
    def post_html(self, sketch_id, object_id):
        self.sketch = SketchModel.get_by_id(int(sketch_id))
        self.sketch_id = sketch_id
        self.sketch_name = self.sketch.name
        self.model_id = object_id
        self.model = ObjectModel.get_by_id(int(object_id), parent=self.sketch)
        if not self.model:
            return self.post_html_error('No model found for %d' % int(object_id))
        if self.request.get('object_type') == 'responsibility':
            return self.post_html_responsibility()
        elif self.request.get('object_type') == 'partner':
            return self.post_html_partner()
        else:
            self.message = 'There was a problem dispatching to %s' % self.request.get('object_type')
            self.render()
            
    def post_html_error(self, message):
        self.message
        self.render()
                        
    def post_html_responsibility(self):
        responsibility = self.request.get('responsibility')
        if 'add' in self.request.arguments():
            self.model.responsibilities.append(responsibility)
        elif 'remove' in self.request.arguments():
            self.model.responsibilities.remove(responsibility)
        self.model.put()
        self.redirect(self.success_url)
        
    def post_html_partner(self):
        partner = ObjectModel.get_by_id(int(self.request.get('partner')), parent=self.sketch).key()
        logging.info('partner = %s' % partner)
        if 'add' in self.request.arguments():
            self.model.partners.append(partner)
        elif 'remove' in self.request.arguments():
            self.model.partners.remove(partner)
        self.model.put()
        self.redirect(self.success_url)
    
        
class TestHandler(LCHandler):
    
    success_url = '/'
    
    def context(self):
        ctx = super(TestHandler, self).context()
        for key in self.request.arguments():
            value = self.request.get_all(key)
            if len(value) > 1:
                ctx[key] = value
            elif len(value) == 1:
                ctx[key] = value[0]
        return ctx
    
    def get(self, template_name):
        self.response.out.write(template.render('templates/%s.html' % template_name, self.context()))


def main():
  application = webapp.WSGIApplication([('/', MainHandler),
                                        ('/test/([\w_]+)', TestHandler),
                                        ('/([\d]+)', SketchHandler),
                                        ('/([\d]+)/([\d]+)', ObjectHandler)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
