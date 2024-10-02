#!/usr/bin/env python3
import json
import logging
import os
import sys
from datetime import datetime
import random

import requests
from openai import OpenAI

from cfg import (OPENAI_API_KEY, OPENAPI_MODEL, PAPERLESS_API_KEY, PAPERLESS_URL, PROMPT, OPENAI_BASEURL, TIMEOUT)
from helpers import make_request, strtobool, get_character_limit


def check_args(doc_pk):
    if not PAPERLESS_API_KEY:
        logging.error("Missing PAPERLESS_API_KEY")
        sys.exit(1)
    if not PAPERLESS_URL:
        logging.error("Missing PAPERLESS_URL")
        sys.exit(1)
    if not OPENAI_API_KEY:
        logging.error("Missing OPENAI_API_KEY")
        sys.exit(1)
    if not OPENAPI_MODEL:
        logging.error("Missing OPENAPI_MODEL")
        sys.exit(1)
    if not doc_pk:
        logging.error("Missing DOCUMENT_ID")
        sys.exit(1)
    if not PROMPT:
        logging.error("Missing PROMPT")
        sys.exit(1)
    if not TIMEOUT:
        logging.error("Missing TIMEOUT")
        sys.exit(1)


def generate_random_hex_color():
    """Generates a random hex color string."""
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def create_new_tag(sess, tag_name, paperless_url):
    """Creates a new tag in Paperless with a random color and returns its ID."""
    url = paperless_url + "/api/tags/"
    body = {
        "name": tag_name,
        "color": generate_random_hex_color()  # Assign random color to the tag
    }
    response = make_request(sess, url, "POST", body=body)
    if not response:
        logging.error(f"could not create tag {tag_name}")
        return None
    logging.info(f"created new tag: {tag_name} with color {body['color']}")
    return response['id']

def get_existing_tags(sess, paperless_url):
    """Retrieves all existing tags from Paperless."""
    url = paperless_url + "/api/tags/"
    response = make_request(sess, url, "GET")
    if not response:
        logging.error("could not retrieve tags")
        return {}
    return {tag['name']: tag['id'] for tag in response['results']}

def get_or_create_tags(sess, tags, paperless_url):
    """Checks if tags exist; if not, creates them with random colors. Returns list of tag IDs."""
    existing_tags = get_existing_tags(sess, paperless_url)
    tag_ids = []
    
    for tag in tags:
        if tag in existing_tags:
            logging.info(f"tag {tag} already exists with id {existing_tags[tag]}")
            tag_ids.append(existing_tags[tag])
        else:
            new_tag_id = create_new_tag(sess, tag, paperless_url)
            if new_tag_id:
                tag_ids.append(new_tag_id)
    
    return tag_ids

def generate_title_and_tags(content, openai_model, openai_key, openai_base_url):
    character_limit = get_character_limit(openai_model)
    now = datetime.now()
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": now.strftime("%m/%d/%Y") + " ".join(content[:character_limit].split())}
    ]
    response = query_openai(model=openai_model,
                            messages=messages,
                            openai_key=openai_key,
                            openai_base_url=openai_base_url,
                            mock=False)
    try:
        logging.info(f"response openai {response}, {response.choices[0].message.content}")
        answer = response.choices[0].message.content
    except:
        return None
    return answer


def query_openai(model, messages, openai_key, openai_base_url, **kwargs):
    client = OpenAI(api_key=openai_key, base_url=openai_base_url)
    args_to_remove = ['mock', 'completion_tokens']

    for arg in args_to_remove:
        if arg in kwargs:
            del kwargs[arg]

    return client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        **kwargs)


def set_auth_tokens(session: requests.Session, api_key):
    session.headers.update(
        {"Authorization": f"Token {api_key}"}
    )


def parse_response(response):
    try:
        data = json.loads(response)
        logging.info(data)
    except:
        return None, None, None
    return data['title'], data.get('explanation', ""), data.get('tags', [])


def update_document_title_and_tags(sess, doc_pk, title, tags, paperless_url):
    """Updates the document title and assigns tag IDs to the document."""
    tag_ids = get_or_create_tags(sess, tags, paperless_url)
    if not tag_ids:
        logging.error(f"could not retrieve or create tags for document {doc_pk}")
        return
    
    url = paperless_url + f"/api/documents/{doc_pk}/"
    body = {"title": title, "tags": tag_ids}
    resp = make_request(sess, url, "PATCH", body=body)
    if not resp:
        logging.error(f"could not update document {doc_pk} title and tags to {title}, {tags}")
        return
    logging.info(f"updated document {doc_pk} title to {title} and added tags {tags}")


def process_single_document(
        sess,
        doc_pk,
        doc_title,
        doc_contents,
        paperless_url,
        openai_model,
        openai_key,
        openai_base_url,
        dry_run=False):
    """Processes a single document: generates a title and tags, then updates the document."""
    response = generate_title_and_tags(doc_contents, openai_model, openai_key, openai_base_url)
    if not response:
        logging.error(f"could not generate title or tags for document {doc_pk}")
        return
    title, explain, tags = parse_response(response)
    if not title:
        logging.error(f"could not parse response for document {doc_pk}: {response}")
        return
    logging.info(f"will update document {doc_pk} title from {doc_title} to: {title} because {explain}, with tags {tags}")

    # Update the document
    if not dry_run:
        update_document_title_and_tags(sess, doc_pk, title, tags, paperless_url)


def get_single_document(sess, doc_pk, paperless_url):
    url = paperless_url + f"/api/documents/{doc_pk}/"
    return make_request(sess, url, "GET")


def run_for_document(doc_pk):
    check_args(doc_pk)

    with requests.Session() as sess:
        set_auth_tokens(sess, PAPERLESS_API_KEY)

        doc_info = get_single_document(sess, doc_pk, PAPERLESS_URL)
        if not isinstance(doc_info, dict):
            logging.error(f"could not retrieve document info for document {doc_pk}")
            return

        doc_contents = doc_info["content"]
        doc_title = doc_info["title"]

        process_single_document(
            sess,
            doc_pk,
            doc_title,
            doc_contents,
            PAPERLESS_URL,
            OPENAPI_MODEL,
            OPENAI_API_KEY,
            OPENAI_BASEURL,
            DRY_RUN)


if __name__ == '__main__':
    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=LOGLEVEL)
    DRY_RUN = strtobool(os.getenv("DRY_RUN", "false"))
    if DRY_RUN:
        logging.info("DRY_RUN ENABLED")
    run_for_document(os.getenv("DOCUMENT_ID"))
