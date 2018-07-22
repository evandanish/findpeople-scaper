#!/usr/bin/python3
"""
FindPeople Scraper
"""
import collections
import argparse
import time
import sys
import requests
from bs4 import BeautifulSoup

RATE_LIMIT_DELAY = 5

ALL = "all"
STUDENT = "student"
EMPLOYEE = "employee"

ContactInfo = collections.namedtuple(
    "ContactInfo",
    ["name",
     "email",
     "dotname",
     "major",
     "org"])


class InvalidRequest(Exception):
    """invalid request argument"""
    pass

class RequestFailure(Exception):
    """Failed to make request"""
    pass

def do_request(firstname, lastname, dot_name="", category=ALL):
    """perform a request and return the body of the result"""
    if category not in (ALL, STUDENT, EMPLOYEE):
        raise InvalidRequest("invalid category")

    form_data = {"filter" : category,
                 "firstname" : firstname,
                 "lastname" : lastname,
                 "name_n" : dot_name}
    resp = requests.post("https://www.osu.edu/findpeople/",
                         data=form_data,
                         )
    if resp.status_code != 200:
        raise RequestFailure("Bad status code: {}".format(resp.status_code))
    return resp.content

def parse_record_email(record):
    """parse an email from the record"""
    email_tags = record.find_all("td", "record-data-email")
    if not email_tags:
        return None
    email_tag = email_tags[0]
    if not email_tag.contents:
        return None
    link_tag = email_tag.contents[0]
    if not link_tag.contents:
        return None
    email = link_tag.contents[0]
    return email

def parse_record_name(record):
    """parse an name from the record"""
    name_tags = record.find_all("th", "record-data-name")
    if not name_tags:
        return None
    name_spans = name_tags[0].find_all("span", "results-name")
    if not name_spans:
        return None
    name_span = name_spans[0]
    if not name_span.contents:
        return None
    name = name_span.contents[0]
    name = name.strip()
    return name

def parse_record_major(record):
    """parse major info from the record"""
    major_tags = record.find_all("td", "record-data-major")
    if not major_tags:
        return None
    major_tag = major_tags[0]
    if not major_tag.contents:
        return None
    return major_tag.contents[0]

def parse_record_org(record):
    """parse org info from the record"""
    org_tags = record.find_all("td", "record-data-org")
    if not org_tags:
        return None
    org_tag = org_tags[0]
    if not org_tag.contents:
        return None
    return org_tag.contents[0]

def parse_emails(response):
    """parse contact info from response and return list"""
    soup = BeautifulSoup(response, "html.parser")
    info = []
    person_records = soup.find_all("tr", "record-data")
    for record in person_records:
        email = parse_record_email(record)
        name = parse_record_name(record)
        major = parse_record_major(record)
        org = parse_record_org(record)
        if email:
            dotname = email.partition("@")[0]
            info.append(ContactInfo(name, email, dotname, major, org))
    return info

def err(msg):
    """Print error to stderr"""
    if msg and msg[-1] != "\n":
        msg = msg + "\n"
    sys.stderr.write(msg)

def contact_to_str(contact):
    """Convert contact info to string repr"""
    result = "{} \n\temail: {}".format(contact.name, contact.email)
    if contact.major:
        result += "\n\tmajor: {}".format(contact.major)
    if contact.org:
        result += "\n\torg: {}".format(contact.org)
    return result

def main():
    """main"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name",
                        type=str,
                        help="Name to search for")
    parser.add_argument("-t", "--type",
                        choices=(ALL, STUDENT, EMPLOYEE),
                        default=ALL,
                        help="Affiliation for search")
    parser.add_argument("-b", "--batch",
                        type=argparse.FileType('r'),
                        help="list of names separated by newlines")
    parser.add_argument("-o", "--output",
                        type=argparse.FileType("w"),
                        default=sys.stdout,
                        help="where to store whatever we find")
    parser.add_argument("-r", "--ratelimit",
                        type=int,
                        default=RATE_LIMIT_DELAY,
                        help="minimum delay between queries")
    parser.add_argument("-f", "--file",
                        type=argparse.FileType('r'),
                        help="parse existing html file and exit")

    args = parser.parse_args()

    if args.file:
        data = args.file.read()
        info = parse_emails(data)
        for i in info:
            args.output.write(contact_to_str(i))
            args.output.write("\n")
            args.output.flush()
        if not info:
            err("Could not find records in input file")
        return

    names = []

    if args.name:
        #Assume lastname if only one word given
        parts = args.name.split()
        if len(parts) == 1:
            names.append(("", parts[0]))
        else:
            names.append((parts[0], parts[-1]))

    if args.batch:
        for line in args.batch:
            parts = line.strip().split()
            if len(parts) == 1:
                names.append(("", parts[0]))
            elif len(parts) > 1:
                names.append((parts[0], parts[-1]))

    start_time = time.time() - args.ratelimit

    if not names:
        err("provide name with '-b' or '-n' option. See help for details")

    for name in names:
        delay = start_time + args.ratelimit - time.time()
        if delay > 0:
            time.sleep(delay)
        start_time = time.time()
        data = do_request(name[0], name[1])
        info = parse_emails(data)
        for i in info:
            args.output.write(contact_to_str(i))
            args.output.write("\n")
            args.output.flush()
        if not info:
            err("Failed to find record for name: {}".format(name))


if __name__ == "__main__":
    main()
