import tornado.ioloop
import tornado.web
import datetime
import pymongo
import json
import logging
logging.basicConfig(level="INFO")

from tornado.web import HTTPError
from dictshield.document import Document
from dictshield.fields.mongo import ObjectIdField
from dictshield.fields import (StringField, 
                               BooleanField, 
                               EmailField,
                               DateTimeField)


class Signature(Document):
    first_name = StringField(max_length=200, required=True)
    last_name = StringField(max_length=200, required=True)
    organisation = StringField(max_length=200)
    email = EmailField(max_length=200, required=True)
    comment = StringField(max_length=140)
    is_australian = BooleanField(required=True)
    pid = ObjectIdField(required=True) 
    signed_on = DateTimeField(required=True)


class Petition(Document):
    sid = StringField(max_length=4096)
    title = StringField(max_length=4096)
    message = StringField(max_length=4096)


def get_fields(shield):
    x = shield.to_python()
    for k in shield._fields.keys():
        if k not in x:
            x[k] = ""
    del x["_types"]
    del x["_cls"]
    return x


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


def create_table(table, headers=None):
    x = []

    for row in table:
        x.append("<td>" + "</td><td>".join(row) +  "</td>")
    
    tbody = "<tbody><tr>" + "</tr><tr>".join(x) + "</tr></tbody>"
    
    thead = ""
    if headers:
        thead = "<thead><th>" + "</th><th>".join(headers) + "</th></thead>"
    
    return "<table>" + thead + tbody + "</table>"


def create_css():
    return """<style type="text/css">
        body {
            font-family: sans-serif;
            background-color: #ccc;
        }
        td {
            vertical-align: top;
        }
        .signature-form, .share-box {
            float: right;
            clear: right;
            border: 1px solid gray;
            background-color: #eee;
            margin-left: 6px;
            margin-bottom: 6px;
            padding: 6px;
            width: 280px;
        }
        .share-box iframe {
            float: left;
        }
        .header {
            background-color: white;
            border: 1px solid gray;
            max-width: 800px;
            padding: 6px;
        }
        .header td {
            vertical-align: middle;
        }
        .header h1 {
            text-align: center;
        }
        .signature-form h2 {
            text-align: center;
        }
        .signature-form .error {
            color: red;
        }
        .signature-form .error > input {
            background-color: pink;
        }
        .signature-form label {
            display: block;
        }
        .signature-form input[type='text'], 
        .signature-form input[type='email'],
        .signature-form input[type='submit'],
        .signature-form textarea {
            box-sizing: border-box;
            width: 100%;
            margin-bottom: 6px;
        }
        .signature-form table {
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


def create_share_box():
    return """<div class='share-box'>
        <a href="https://twitter.com/piratepartyau" class="twitter-follow-button" data-show-count="false">Follow @piratepartyau</a>
        <script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src="//platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>
        <a href="https://twitter.com/intent/tweet?button_hashtag=natsecinquiry&text=I%20just%20signed%20the%20senate%20petition%20regarding%20the%20National%20Security%20Inquiry%20here:" class="twitter-hashtag-button" data-related="piratepartyau" data-url="http://pirateparty.org.au/natsecinquiry-petition">Tweet #natsecinquiry</a>
        <script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src="//platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>
    </div>"""


def create_signature_form(values={}, invalid=[], error_msg=""):
    form = """<form class='signature-form' method="post">
        <h2>Sign the petition!</h2>
        {error_msg}
        <table role='presentation'>
            <tbody>
                <tr>
                    <td class="{first_name_label}" style="width: 50%">
                        <label for='first_name'>First name</label>
                        <input type='text' id='first_name' name="first_name" value="{first_name}">
                    </td>
                    <td class="{last_name_label}" style="width: 50%">
                        <label for='last_name'>Last name</label>
                        <input type='text' id='last_name' name="last_name" value="{last_name}">
                    </td>
                </tr>
                <tr>
                    <td colspan='2'>
                        <label for='organisation'>Organisation <small>(optional)</small></label>
                        <input type='text' id='organisation' name='organisation' value="{organisation}">
                    </td>
                </tr>
                <tr>
                    <td class="{email_label}" colspan='2'>
                        <label for='email'>Email address</label>
                        <input type='email' id='email' name='email' value="{email}">
                    </td>
                </tr>
                <tr>
                    <td colspan='2'>
                        <label for='comment'>Comment <small>(optional, max 140 chars)</small></label>
                        <textarea id='comment' name='comment'>{comment}</textarea>
                    </td>
                </tr>
                <tr>
                    <td class="{is_australian_label}" colspan='2'>
                        <span>Are you Australian?</span>
                        <div class='radio'>
                            <input type='radio' id="is_australian_true" name="is_australian" {is_australian_true} value="true"> Yes
                        </div>
                        <div class='radio'>
                            <input type='radio' id="is_australian_false" name="is_australian" {is_australian_false} value="false"> No
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

    o = values
    missing = False

    for name in ['first_name', 'last_name', 'email', 'is_australian']:
        if name in invalid:
            o[name + "_label"] = "error"
            missing = True
        else: 
            o[name + "_label"] = ""
    
    o['is_australian_false'] = ""
    o['is_australian_true'] = ""
    
    if o.get('is_australian') == True:
        o['is_australian_true'] = "checked"
    elif o.get('is_australian') == False:
        o['is_australian_false'] = "checked"
    
    if missing:
        error_msg = "<div class='error'>There are incomplete fields.</div>"
    
    return form.format(error_msg=error_msg, **o)


class SignatureHandler(tornado.web.RequestHandler):
    def get(self, petition_id):
        petition = db.petitions.find_one({"sid": petition_id})
        if petition is None:
            raise HTTPError(404)

        signatures = db.signatures.find({"pid": petition['_id']})
        signatures = [Signature(**signature) for signature in signatures]

        headers = ['First Name', 'Last Name', 'Organisation', 'Email', 'Is Australian?', 'Comments']
        table = []
        for s in signatures:
            row = []
            row.append(s.first_name)
            row.append(s.last_name)
            row.append(s.organisation or "")
            row.append(s.email)
            row.append(str(s.is_australian))
            row.append(s.comment or "")
            table.append(row)
        table = create_table(table, headers)
        
        chunk = "<div class='header'>\n<h1>%s</h1>\n<p>%s</p>\n</div>\n" % (petition['title'], petition['message'])
        body = [chunk, "<hr>", table]
        self.write(create_html5_page(petition_id, [create_css()], body))


class JSONPPetitionHandler(tornado.web.RequestHandler):
    def get(self, petition_id):
        jsonp_method = self.get_argument("jsonp", "jsonp")
        self.set_header("Content-Type", "application/javascript")
        petition = db.petitions.find_one({"sid": petition_id})
        if petition is None:
            raise HTTPError(404)
        del petition['_id']
        self.write(jsonp_method + "(" + json.dumps(petition) + ")")


class JSONPetitionHandler(tornado.web.RequestHandler):
    def get(self, petition_id):
        self.set_header("Content-Type", "application/json")
        petition = db.petitions.find_one({"sid": petition_id})
        if petition is None:
            raise HTTPError(404)
        del petition['_id']
        self.write(json.dumps(petition))


class FaviconHandler(tornado.web.RequestHandler):
    def get(self):
        pass


class PetitionHandler(tornado.web.RequestHandler):
    def get(self, petition_id):
        petition = db.petitions.find_one({"sid": petition_id})
        if petition is None:
            raise HTTPError(404)
        logo = """<a href='http://pirateparty.org.au/'>
            <img src='https://join.pirateparty.org.au/logo.png' class='logo' alt='Pirate Party Australia logo'>
        </a>"""
        chunk = """<div class='header'>
            <table role='presentation'>
                <tr>
                    <td>
                        %s
                    </td>
                    <td>
                        <h1>%s</h1>
                    </td>
                </tr>
            </table>
            <div>%s</div>
        </div>
        """ % (logo, petition['title'], petition['message'])
        head = [create_css()]
        body = [create_signature_form(get_fields(Signature())), create_share_box(), chunk]
        
        self.write(create_html5_page(petition['title'], head, body))


    def post(self, petition_id):
        petition = db.petitions.find_one({"sid": petition_id})
        if petition is None:
            raise HTTPError(404)
        
        sig = Signature()
        sig.pid = petition['_id']
        petition = Petition(**petition)

        sig.first_name = self.get_argument("first_name", None)
        sig.last_name = self.get_argument("last_name", None)
        sig.email = self.get_argument("email", None)
        sig.comment = self.get_argument("comment", None)
        
        is_australian = self.get_argument("is_australian", None)
        if is_australian is not None:
            is_australian = is_australian == "true"
        sig.is_australian = is_australian
        
        sig.signed_on = datetime.datetime.utcnow()
        error_fields = []

        try:
            sig.validate(True)
        except Exception as e:
            error_fields = [error.field_name for error in e.error_list]
        
        logo = """<a href='http://pirateparty.org.au/'>
            <img src='https://join.pirateparty.org.au/logo.png' class='logo' alt='Pirate Party Australia logo'>
        </a>"""
        chunk = """<div class='header'>
            <table role='presentation'>
                <tr>
                    <td>
                        %s
                    </td>
                    <td>
                        <h1>%s</h1>
                    </td>
                </tr>
            </table>
            <div>%s</div>
        </div>
        """ % (logo, petition['title'], petition['message'])
        
		head = [create_css()]
        body = [] 
        
		if len(error_fields) > 0:
            body += [create_signature_form(get_fields(sig), error_fields), create_share_box(), chunk]
        else:
            signature = db.signatures.find_one({"pid": sig.pid, "email": sig.email})
            if signature is not None:
                body.append("<div class='signature-form'>A submission from this email address has previously been received. Thank you for your support.</div>")
                logging.warn("[%s] Email '%s' attempted to sign again." % (self.request.remote_ip, sig.email))
            else:
                db.signatures.insert(sig.to_python())
                body.append("<div class='signature-form'>Submission received. Thank you for your support.</div>")
                logging.info("[%s] Email '%s' signed." % (self.request.remote_ip, sig.email))

            body += [create_share_box(), chunk]

        self.write(create_html5_page(petition['title'], head, body))

'''
class TestHandler(tornado.web.RequestHandler):
    def get(self, petition_id):
        petition = db.petitions.find_one({"sid": petition_id})
        
        head = []
        body = ["<iframe height='500' width='300' src='/" + petition_id + "'></iframe>"]
        self.write(create_html5_page(petition_id, head, body))
'''

db = pymongo.Connection().petitions

application = tornado.web.Application([
    #(r"/signatures/(.*)", SignatureHandler),
    (r"/favicon.ico", FaviconHandler),
    (r"/(.*).jsonp", JSONPPetitionHandler),
    (r"/(.*).json", JSONPetitionHandler),
    (r"/(.*)", PetitionHandler),
], db=db)


if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
