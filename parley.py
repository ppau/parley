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
    comment = StringField(max_length=140)
    is_australian = BooleanField(required=True)
    signed_on = DateTimeField(required=True)


class Petition(Document):
    sid = StringField(max_length=4096)
    title = StringField(max_length=4096)
    message = StringField(max_length=4096)
    signatures = ListField(EmbeddedDocumentField(Signature))


def create_html5_page(title, head=[], body=[]):
    doc = """<!DOCTYPE html>
    <html lang='en'>
        <head>
            <meta charset='utf-8'>
            <title>{title}</title>{head}
        </head>
        <body>{body}</body>
    </html>"""

    return doc.format(
        title=title,
        head="\n" + "\n".join(head),
        body="\n".join(body)
    )


def create_css():
    return """<style type="text/css">
		.signature-form {
			font-family: sans-serif;
		}
        .signature-form label {
            display: block;
        }
		.signature-form input[type='text'], 
		.signature-form input[type='email'],
		.signature-form textarea {
			box-sizing: border-box;
			width: 100%;
		}
		.signature-form textarea {
			resize: vertical;
			min-height: 60px;
		}
		.signature-form .radio {
			display: inline-block; *display: inline; zoom: 1;
			width: 50px;
			padding-left: 10px;
		}
    </style>"""


def create_signature_form():
    return """
    <form class='signature-form' method="post">
        <table role='presentation'>
            <tbody>
                <tr>
                    <td>
                        <label for='first_name'>First name</label>
                        <input type='text' id='first_name' name="first_name">
                    </td>
                    <td>
                        <label for='last_name'>Last name</label>
                        <input type='text' id='last_name' name="last_name">
                    </td>
                </tr>
                <tr>
                    <td colspan='2'>
                        <label for='email'>Email address</label>
                        <input type='email' id='email' name='email'>
                    </td>
                </tr>
                <tr>
                    <td colspan='2'>
                        <label for='comment'>Comment <small>(optional)</small></label>
                        <textarea id='comment' name='comment'></textarea>
                    </td>
                </tr>
                <tr>
                    <td colspan='2'>
                        <span>Are you Australian?</span>
                        <div class='radio'>
                        	<input type='radio' id="is_australian_true" name="is_australian" value="true"> Yes
                        </div>
						<div class='radio'>
							<input type='radio' id="is_australian_false" name="is_australian" value="false"> No
                        </div>
                    </td>
                </tr>
                <tr>
                    <td colspan='2'>
                        <input type='submit' value='Submit'>
                    </td>
                </tr>
            </tbody>
        </table>
    </form>
    """


class PetitionHandler(tornado.web.RequestHandler):
    def get(self, petition_id):
        petition = db.petitions.find_one({"sid": petition_id})
        if petition is None:
            raise HTTPError(404)
        
        chunk = ("<header>\n<h1>%s</h1>\n<p>%s</p>\n</header>\n" 
                % (petition['title'], petition['message']))
		head = [create_css()]
        body = [chunk, create_signature_form()]
        
        self.write(create_html5_page(petition['title'], head, body))


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
