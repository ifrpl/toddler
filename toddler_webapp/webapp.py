__author__ = 'michal'

from flask import Flask, send_from_directory, request, session, abort,\
    make_response, jsonify, Response
import os
import sys
import argparse
import getpass
import json
import uuid
from webapp import auth
from functools import wraps
import pika
from pika.exceptions import AMQPError, AMQPConnectionError, AMQPChannelError

from aiohttp.client import ClientResponse
config = {}

script_root = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = "webapp.conf"

def parse_config(config_filepath):
    config = {}
    try:
        with open(config_filepath) as config_file:
            config = json.load(config_file)
    except FileNotFoundError:

        print("Configuration file not found", file=sys.stderr)
        sys.exit(1)

        pass

    return config

app = Flask(__name__)

def check_csrf(func):
    global app
    @wraps(func)
    def csrf_wrapper(*args, **kwargs):
        nonlocal func
        try:
            csrf_token = request.headers['X-CSRF-TOKEN']

            if csrf_token == session['csrf_token']:
                return func(*args, **kwargs)
            else:
                app.logger.warning("Wrong csrf token")
                abort(401)

        except KeyError as e:
            app.logger.warning("Csrf token not given")
            abort(401, e)

    return csrf_wrapper


def authenticated(func):
    global app
    @wraps(func)
    def auth_wrapper(*args, **kwargs):
        nonlocal func
        try:
            if session['authenticated']:
                return func(*args, **kwargs)
            else:
                raise auth.NotAuthorised
        except (KeyError, auth.NotAuthorised):
            app.logger.info("Not Authorized to access %s" % request.url)
            abort(401)

    return auth_wrapper

@app.route("/api/v1/login", methods=['POST'])
@check_csrf
def login():
    global config

    auth_dict = request.get_json()

    try:
        if auth.auth_user(config, auth_dict['user'], auth_dict['password']):
            session['authenticated'] = True
            return jsonify({"user": auth_dict['user']})
        else:
            app.logger.warning(
                "Tried to authenticate `%s` and failed" % auth_dict['user']
            )
            abort(401)
    except FileNotFoundError as e:
        app.logger.error(e)
        abort(500)

@app.route("/api/v1/is-logged-in")
@check_csrf
@authenticated
def is_logged_in():
    return jsonify({"logged_in": True})

@app.route("/api/v1/logout")
@check_csrf
@authenticated
def logout():
    session['authenticated'] = False
    return jsonify({})


def publish_message(msg):
    """
    Publishes message to rabbit in a blocking manner
    :param msg: Message that will be encoded as json
    :return Response:
    """
    global config
    data = request.get_json()
    params = pika.ConnectionParameters()
    params.host = config['rabbitHost']
    params.port = config['rabbitPort']
    # params.virtual_host = "rabbit"
    params.credentials = pika.PlainCredentials(
        config['rabbitUser'],
        config['rabbitPassword']
    )

    try:
        connection = pika.BlockingConnection(params)

        channel = connection.channel()

        channel.queue_declare(
            queue="urls",
            durable=True,
            exclusive=False,
            auto_delete=True
        )

        channel.confirm_delivery()

        if channel.basic_publish(
                exchange="urls",
                routing_key="urls",
                body=json.dumps(msg),
                properties=pika.BasicProperties(
                        content_type="application/json",
                        delivery_mode=1
                )):
            connection.close()
            return jsonify({"confirmed": True})
        else:
            connection.close()
            return jsonify({"confirmed": False})
    except (AMQPError, AMQPConnectionError, AMQPChannelError) as e:
        app.logger.exception(e)
        response = jsonify({"error": "Received error %s" % str(e)})
        """:type: Response"""
        response.status_code = 500
        return response

@app.route("/api/v1/update-url", methods=['POST'])
@check_csrf
@authenticated
def update_url():
    return publish_message({
        "url": "url",
        "action": "update"
    })

@app.route("/api/v1/delete-url", methods=['POST'])
@check_csrf
@authenticated
def delete_url():
    return publish_message({
        "url": "url",
        "action": "delete"
    })

#static files serving:
@app.route("/static/b/<path:filename>")
def static_proxy_bower(filename):
    return send_from_directory(
        os.path.join(script_root, "bower_components"),
        filename
    )
@app.route("/static/<path:filename>")
def static_proxy(filename):
    return send_from_directory(
        os.path.join(script_root, "static"),
        filename
    )
@app.route("/", defaults={'route': ''})
@app.route("/<path:route>")
def index(route):
    response = make_response(app.send_static_file("index.html"))
    csrf_token = str(uuid.uuid4())
    response.set_cookie("csrf_token", csrf_token.encode("utf8"))
    session['csrf_token'] = csrf_token

    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--serve", default=True, action='store_true')
    parser.add_argument("--config")
    parser.add_argument("--debug", default=True, action='store_true')
    parser.add_argument("--add-user", default=False, action='store_true')
    parser.add_argument("--user-name")

    args = parser.parse_args()

    if args.config:
        CONFIG_FILE = args.config

    print("Using config file %s" % CONFIG_FILE)

    config = parse_config(CONFIG_FILE)

    if args.add_user:
        if args.user_name == "" or args.user_name is None:
            user = input("User name: ")
        else:
            user = args.user_name

        password = getpass.getpass("Password: ")

        auth.add_user(config, user, password)

        sys.exit(0)

    if args.serve:
        try:
            app.secret_key = config['secret']
            if args.debug:
                app.debug = True
            app.run()
            sys.exit(0)
        except KeyError:
            sys.exit(1)




