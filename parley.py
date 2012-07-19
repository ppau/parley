import tornado.ioloop
import tornado.web
import datetime
import pymongo

from tornado.web import HTTPError
from dictshield.document import Document, EmbeddedDocument
from dictshield.forms import Form
from dictshield.fields.compound import ListField, EmbeddedDocumentField
from dictshield.fields import (StringField, 
                               BooleanField, 
                               EmailField, 
                               DateTimeField)


class Signature(EmbeddedDocument):
    first_name = StringField(max_length=200, required=True)
    last_name = StringField(max_length=200, required=True)
    email = EmailField(max_length=200, required=True)
    is_australian = BooleanField(required=True)
    signed_on = DateTimeField(required=True)


class Petition(Document):
    sid = StringField(max_length=4096)
    title = StringField(max_length=4096)
    message = StringField(max_length=4096)
    signatures = ListField(EmbeddedDocumentField(Signature))



class PetitionHandler(tornado.web.RequestHandler):
    def get(self, petition_id):
        petition = db.petitions.find_one({"title", petition_id})
        if petition is None:
            raise HTTPError(404)
        
        self.write(petition.to_json())

    def post(self, petition_id):
        sig = Signature()
        sig.first_name = self.get_argument("first_name")
        sig.last_name = self.get_argument("last_name")
        sig.email = self.get_argument("email")
        sig.is_australian = self.get_argument("is_australian") == "true"
        sig.signed_on = datetime.datetime.utcnow()
        self.write(sig.to_json())


db = pymongo.Connection().petitions

application = tornado.web.Application([
    (r"/(.*)", PetitionHandler),
], db=db)

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
