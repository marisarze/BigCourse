#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import uuid
import re
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
from scoring import get_score
from scoring import get_interests

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field:
    """ Base class for all Fields. Every field needs an initial value """

    def __init__(self, required=False, nullable=True):
        self.required = required
        if nullable:
            self.initial_value = None

    def validate(self, value):
        """ Check if this is a valid value for this field """
        return False


class CharField(Field):
    def validate(self, value):
        return isinstance(value, str)


class ArgumentsField(Field):
    def validate(self, value):
        if isinstance(value, dict):
            return True
        return False



class EmailField(Field):
    def validate(self, value):
        return len(re.findall(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", em))>0


class PhoneField(Field):
    def validate(self, value):
            try:
                number = int(value)
                if all(number >= 7 * 10**10, number < 8 * 10**10):
                    return True
            except:
                return False


class DateField(Field):
    def validate(self, value):
        try:
            datetime.datetime.strptime(value, '%d.%m.%Y')
            return True
        except:
            return False


class BirthDayField(DateField):
    def validate(self, value):
        try:
            dt = datetime.datetime.strptime(value, '%d.%m.%Y')
            return dt.year >= datetime.datetime.today().year - 70
        except:
            return False


class GenderField(Field):
    def validate(self, value):
        return value in (1, 2, 3)


class ClientIDsField(Field):
    def validate(self, value):
        if isinstance(value, (tuple, list, set)):
            return all([i for i in map(lambda x: type(x) == int, value)])
        return False


class ORMMeta(type):
    """ Metaclass of our fields """
    
    def __new__(self, class_name, bases, namespace):
        fields = {
            name: field
            for name, field in namespace.items() if isinstance(field, Field)
        }

        new_namespace = namespace.copy()
        for name in fields.keys():
            del new_namespace[name]
        new_namespace['_fields'] = fields
        return super().__new__(self, class_name, bases, new_namespace)


class ORMBase(metaclass=ORMMeta):
    """ User interface for the base class """

    def __init__(self, kwargs):
        self.validate(kwargs)        


    def validate(self, kwargs):
        class_name = self.__class__.__name__
        _required = []
        for name in self._fields.keys():
            if self._fields[name].required and (name not in kwargs.keys()):
                _required.append(name)
        if _required:
            raise AttributeError('Additional fields are required to create class {}: {} '.format(self.class_name, ', '.join(_required)))
        for key, value in kwargs.items():
            setattr(self, key, value)


    def __setattr__(self, key, value):
        """ Magic method setter """
        if key in self._fields:
            if self._fields[key].validate(value):
                super().__setattr__(key, value)
            else:
                raise AttributeError('Invalid value "{}" for field {} in class "{}"'.format(value, key, self.class_name))
        else:
            raise AttributeError('Unknown field "{}" in class {}'.format(key, self.class_name))

    def get_fields(self):
        """ Collect to dictionary all field elements """
        new_dictionary = {}
        allattrs = [name for name in dir(self) if name in self._fields.keys()]
        for name in allattrs:
            new_dictionary[name] = getattr(self, name)

        return new_dictionary


class ClientsInterestsRequest(ORMBase):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(ORMBase):
    first_name = CharField(required=True, nullable=True)
    last_name = CharField(required=True, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def validate(self, kwargs):
        variants = [['phone', 'email'],
                    ['name', 'last_name'],
                    ['gender', 'birthday']]
        cases = []
        for pair in variants:
            case = True
            for name in pair:
                case = case and (name in kwargs.keys())
            cases.append(case)
        if not any(cases):
            raise AttributeError("There are not any pairs in arguments: phone-email, name-last_name, gender-birthday")
        super().validate(kwargs)


class MethodRequest(ORMBase):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    
    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode('utf-8')).hexdigest()
    else:
        digest = hashlib.sha512((request.account + request.login + SALT).encode('utf-8')).hexdigest()
    print('digest is : ', digest)
    print('tiken is : ', request.token)
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    response, code = None, None
    request_body = request['body']
    try:
        main_request = MethodRequest(request_body)
        if not check_auth(main_request):
            code = 403
            return response, code
        if main_request.method == 'online_score':
            auxilary_request = OnlineScoreRequest(main_request.arguments)
            ctx['has'] = [i for i in auxilary_request.get_fields().keys()]
            if  not main_request.is_admin:
                response = {"score": 42}
            else:
                response = {"score": get_score(None, auxilary_request.get_field_values)}    
        elif main_request.method == 'clients_interests':
            auxilary_request = ClientsInterestsRequest(main_request.arguments)
            ctx['nclients'] = len(auxilary_request.client_ids)
            for id in auxilary_request.client_ids:
                response[id] = get_interests(None, id)
        code = 200
        return response, code
    except AttributeError as e:
        response = {"code": 422, "error": e.args[0]}
        code = 422

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        print('------------------------------------------------------------------------')
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            print('headers: ', self.headers, end='\n')
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
            print('request in DOPOST: ', request, end='\n')
        except:
            print('bad_code', end='\n')
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s \n" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND
        print('code is:', code)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s \n', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
