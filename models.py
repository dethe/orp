from google.appengine.ext import db
from google.appengine.api import users

class ObjectModel(db.Model):

    name = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    responsibilities = db.ListProperty(item_type=str)
    partners = db.ListProperty(item_type=db.Key)
    
    def __str__(self):
        return self.name
        return '%s, %d responsibilities, %d partners' % (self.name, len(self.responsibilities), len(self.partners))
        
    @property
    def id(self):
        return self.key().id()

    @property
    def action_url(self):
        return '/%d/%d' % (self.sketch.key().id(), self.key().id())
        
        
class SketchModel(db.Model):
    
    owner = db.UserProperty()
    name = db.StringProperty(required=True)
    objects = db.ListProperty(item_type=db.Key)
    members = db.ListProperty(item_type=db.Key)
    
    def __str__(self):
        return self.name
        return '%s, %d objects, %d members' % (self.name, self.objects.count(), self.members.count())
    
    @property
    def action_url(self):
        return '/%d' % self.key().id()
        
        
