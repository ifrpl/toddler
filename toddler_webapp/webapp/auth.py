__author__ = 'michal'

import hashlib
import functools
import re
from flask import session, request, abort

class NotAllowed(Exception): pass
class NotAuthorised(Exception): pass



def _hash(config, *strings):
    secret = config['secret']
    hash = hashlib.sha384()
    to_hash = secret+"".join(strings)
    hash.update(to_hash.encode("utf8"))
    return hash.hexdigest()


def auth_user(config, user, password):

    try:
        password_file_path = config['passwordFile']
    except KeyError as e:
        raise FileNotFoundError("No password file configured")

    with open(config['passwordFile']) as passwords_file:

        def check_user(previous_result, password_line):
            nonlocal  user, password
            if previous_result is None:
                matches = re.findall(r"(.+):([a-f0-9]+)", password_line)
                try:
                    ch_user, ch_digest = matches[0]
                    if matches[0][0] != user:
                        return None
                    else:
                        digest = _hash(config, password, user)
                        if digest == ch_digest:
                            return True
                        else:
                            return False
                except ValueError:
                    return None
            else:
                return previous_result

        return functools.reduce(
            check_user,
            passwords_file.readlines(),
            None
        ) or False


def add_user(config, user, password):
    """

    :param config:
    :param user:
    :param password: not hashed password
    :return:
    """
    digest = _hash(config, password, user)

    with open(config['passwordFile'], "a") as passwords_file:
        line = "%s:%s\n" % (user, digest)
        passwords_file.write(line)

    return True
