__author__ = 'michal'

"""
= Crawl configuration importer =
"""

from bs4 import BeautifulSoup, Tag
import re
from functools import reduce
from ..logging import setup_logging


def extract_hostname(regexp):

    groups = re.match("(https?://)([a-z0-9\-\.]+)/.*", regexp)
    if groups is not None:
        return ''.join((groups.group(1), groups.group(2)))
    else:
        return None


def convert_regexp(regexp, hostname=None):

    if hostname:
        regexp = '/'.join((hostname, regexp))

    def _surround_by_not(string, char):

        find_pattern = "([A-Za-z0-9\-_/])" + ("(\\%s)" % char)\
                       + "([/A-Za-z0-9\-_\*\\\\])"
        def _match(match):
            m = (match.group(1) + "\0" + char + "\0" + match.group(3))
            return m

        return re.sub(
            re.compile(find_pattern),
            _match,
            string
        )
    # find hard dots, and mark them with nots

    to_be_notted = ('.', '?', '&')
    converted = reduce(_surround_by_not, to_be_notted, regexp)

    convert_list = (
        ("\*", "*"),
        ("\.", "."),
        ("\+", "+"),
        ("\[", "["),
        ("\]", "]"),
        ("\(", "("),
        ("\)", ")"),
        ("\{", "{"),
        ("\}", "}"),
        ("\?", "?"),
        ("\^", "^"),
        ("\$", "$"),
        ("\|", "|")
    )

    def replace(c_str, converts):
        return c_str.replace(*converts)

    converted = reduce(replace, convert_list, converted)

    def _remove_nots(string, not_char):
        return string.replace("\0%s\0" % not_char, "\\"+not_char)

    converted = reduce(_remove_nots, to_be_notted, converted)

    return converted


def get_configuration(xml_string, log=None):
    """
    == Configuration importing ==
    This functions converts xml to toddler configuration, well not exactly
    it returns a dictionary for crawlConfig option in (Host)[/models.py#Host]
    model.

    Result looks smth like this:

        {
            "example.com": [
                {
                    "pattern": "http://example\.com/"
                    "actions": ["index", "follow"]
                }
            ]
        }


    :param xml_string:
    :return dict:
    """

    if log is None:
        log = setup_logging()

    log.info("Starting to process xml file: {} bytes".format(len(xml_string)))
    soup = BeautifulSoup(xml_string, ['lxml', 'xml'])
    log.info("Finished processing xml file.")
    result_dict = {}
    actions = ('index', 'follow', 'accept', 'nofollow', 'noindex')
    for rules_tag in soup.find_all("Rules"):
        try:
            log.info("Processing Rules: {}".format(rules_tag['group']))
        except KeyError:
            continue
        order = 1

        def convert_to_dict(rule_tag: Tag):
            nonlocal order
            ret_dict = {}
            atom = rule_tag.find("Atom")
            try:
                pattern = atom['value']

                ret_dict['order'] = order
                # some fixes for rule kinds
                # we've got: prefix, inside, suffix, exact
                if atom['kind'] == "prefix":
                    ret_dict['pattern'] = pattern + "\.\*"
                elif atom['kind'] == "inside":
                    ret_dict['pattern'] = "\.\*"+pattern+"\.\*"
                elif atom['kind'] == "suffix":
                    ret_dict['pattern'] = "\.\*"+pattern
                else:
                    ret_dict['pattern'] = pattern
                ret_dict['actions'] = []
                for action in rule_tag.children:
                    if action is not None:
                        try:
                            if action.name.lower() in actions:
                                ret_dict['actions'].append(action.name.lower())
                        except AttributeError:
                            pass
                order += 1
                return ret_dict
            except TypeError:
                return None

        rule_tags = [rule_dict for rule_dict in
                     [convert_to_dict(rule_tag) for rule_tag
                      in rules_tag.children]
                     if rule_dict is not None]

        hostname = None
        unordered_rules = []
        no_hostname_counter = len(rule_tags)

        while len(rule_tags) > 0:
            rule = rule_tags.pop(0)
            extracted_hostname = extract_hostname(rule['pattern'])
            if extracted_hostname is None and hostname is None:
                rule_tags.append(rule)
                no_hostname_counter -= 1
                if no_hostname_counter < 0:
                    break
                continue
            else:
                if extracted_hostname is None and hostname is not None:
                    rule['pattern'] = convert_regexp(rule['pattern'], hostname)
                else:
                    hostname = extracted_hostname
                    rule['pattern'] = convert_regexp(rule['pattern'])

            unordered_rules.append(rule)

        # order as it was in xml:
        ordered_rules = []
        order = 1
        while len(unordered_rules) > 0:
            rule = unordered_rules.pop(0)
            if rule['order'] == order:
                del rule['order']
                ordered_rules.append(rule)
                order += 1
            else:
                unordered_rules.append(rule)
        if len(ordered_rules) > 0:
            yield (re.sub("https?://", "", hostname), ordered_rules)


