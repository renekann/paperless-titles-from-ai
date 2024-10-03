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

def get_document_created_date(doc_info):
    """Returns the created date of the document or None if not available."""
    return doc_info.get("created_date")

def generate_random_hex_color():
    """Generates a random hex color string."""
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def create_new_tag(sess, tag_name, paperless_url):
    """Creates a new tag in Paperless with a random color and returns its ID."""
    url = paperless_url + "/api/tags/"
    color = generate_random_hex_color()
    body = {
        "name": tag_name,
        "color": color,
        "owner": "3"
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

def get_existing_correspondents(sess, paperless_url):
    """Retrieves all existing correspondents from Paperless."""
    url = paperless_url + "/api/correspondents/"
    response = make_request(sess, url, "GET")
    if not response:
        logging.error("could not retrieve correspondents")
        return {}
    return {correspondent['name']: correspondent['id'] for correspondent in response['results']}

def create_new_correspondent(sess, correspondent_name, paperless_url):
    """Creates a new correspondent in Paperless and returns its ID."""
    url = paperless_url + "/api/correspondents/"
    body = {
        "name": correspondent_name,
        "owner": "3"
    }
    response = make_request(sess, url, "POST", body=body)
    if not response:
        logging.error(f"could not create correspondent {correspondent_name}")
        return None
    logging.info(f"created new correspondent: {correspondent_name}")
    return response['id']

def get_or_create_correspondent(sess, correspondent, paperless_url):
    """Checks if a correspondent exists; if not, creates it and returns the correspondent ID."""
    existing_correspondents = get_existing_correspondents(sess, paperless_url)
    
    if correspondent in existing_correspondents:
        logging.info(f"correspondent {correspondent} already exists with id {existing_correspondents[correspondent]}")
        return existing_correspondents[correspondent]
    else:
        new_correspondent_id = create_new_correspondent(sess, correspondent, paperless_url)
        if new_correspondent_id:
            return new_correspondent_id
        else:
            logging.error(f"could not create or find correspondent {correspondent}")
            return None


def generate_title_tags_and_correspondent(content, openai_model, openai_key, openai_base_url):
    """Generates title, tags, correspondent, and extracts the most relevant date from the content."""
    character_limit = get_character_limit(openai_model)
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": " ".join(content[:character_limit].split())}
    ]
    response = query_openai(model=openai_model,
                            messages=messages,
                            openai_key=openai_key,
                            openai_base_url=openai_base_url,
                            mock=False)
    try:
        answer = response.choices[0].message.content
    except:
        return None
    return answer

def get_custom_fields(sess, paperless_url):
    """Retrieves all existing custom fields from Paperless."""
    url = paperless_url + "/api/custom_fields/"
    response = make_request(sess, url, "GET")
    if not response:
        logging.error("could not retrieve custom fields")
        return {}
    return {field['name']: field['id'] for field in response['results']}

def create_custom_field(sess, field_name, paperless_url):
    """Creates a new custom field in Paperless and returns its ID."""
    url = paperless_url + "/api/custom_fields/"
    body = {
        "name": field_name,
        "data_type": "string",
        "extra_data": 'null'
    }
    response = make_request(sess, url, "POST", body=body)
    if not response:
        logging.error(f"could not create custom field {field_name}")
        return None
    logging.info(f"created new custom field: {field_name}")
    return response['id']

def get_or_create_custom_field(sess, field_name, paperless_url):
    """Checks if a custom field exists; if not, creates it and returns its ID."""
    custom_fields = get_custom_fields(sess, paperless_url)
    
    if field_name in custom_fields:
        logging.info(f"custom field {field_name} already exists with id {custom_fields[field_name]}")
        return custom_fields[field_name]
    else:
        new_field_id = create_custom_field(sess, field_name, paperless_url)
        if new_field_id:
            return new_field_id
        else:
            logging.error(f"could not create or find custom field {field_name}")
            return None

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
    """Parses the response to extract title, explanation, tags, correspondent, and created_date."""
    try:
        data = json.loads(response)
    except:
        return None, None, None, None, None, None
    return data['title'], data.get('explanation', ""), data.get('tags', []), data.get('correspondent', ""), data.get('created_date', ""), data.get('summary', "")


def update_document_title_tags_and_correspondent(sess, doc_pk, title, tags, correspondent, created_date, paperless_url):
    """Updates the document title, tags, and correspondent."""
    
    # Get or create the correspondent and its ID
    correspondent_id = get_or_create_correspondent(sess, correspondent, paperless_url)
    if not correspondent_id:
        logging.error(f"could not retrieve or create correspondent for document {doc_pk}")
        return

    # Get or create tags and their IDs
    tag_ids = get_or_create_tags(sess, tags, paperless_url)
    if not tag_ids:
        logging.error(f"could not retrieve or create tags for document {doc_pk}")
        return

    # Update the document with the title, tags, and correspondent
    url = paperless_url + f"/api/documents/{doc_pk}/"
    body = {"title": title, "tags": tag_ids, "correspondent": correspondent_id}
    resp = make_request(sess, url, "PATCH", body=body)
    if not resp:
        logging.error(f"could not update document {doc_pk} title, tags, and correspondent to {title}, {tags}, {correspondent}")
        return
    logging.info(f"updated document {doc_pk} title to {title}, added tags {tags}, and correspondent {correspondent}")

def update_document_with_custom_fields(sess, doc_pk, custom_field_id, summary_value, paperless_url):
    """Updates the document with the generated summary in the custom field."""
    url = paperless_url + f"/api/documents/{doc_pk}/"
    body = {
        "custom_fields": [{"field": custom_field_id, "value": summary_value}]
    }
    resp = make_request(sess, url, "PATCH", body=body)
    if not resp:
        logging.error(f"could not update document {doc_pk} with custom field {custom_field_id} and value {summary_value}")
        return
    logging.info(f"updated document {doc_pk} with summary: {summary_value}")

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
    """Processes a single document: generates a title, tags, correspondent, and summary, then updates the document."""
    
    # Get document information, including created date
    doc_info = get_single_document(sess, doc_pk, paperless_url)
    if not doc_info:
        logging.error(f"could not retrieve document info for document {doc_pk}")
        return

    # Call OpenAI to generate title, tags, correspondent, created_date, explanation, and summary
    response = generate_title_tags_and_correspondent(doc_contents, openai_model, openai_key, openai_base_url)
    if not response:
        logging.error(f"could not generate title, tags, correspondent, or summary for document {doc_pk}")
        return
    
    # Parse response from OpenAI
    title, explain, tags, correspondent, suggested_created_date, summary = parse_response(response)
    if not title or not summary:
        logging.error(f"could not parse response for document {doc_pk}: {response}")
        return
    
    # Determine the final created date to use (existing created_date or suggested one)
    created_date = get_document_created_date(doc_info) or suggested_created_date or datetime.now().strftime('%Y-%m-%d')
    
    # Combine the final created date with the title
    full_title = f"{created_date} - {title}"
    
    logging.info(f"will update document {doc_pk} title from {doc_title} to: {full_title} because {explain}, with tags {tags} and correspondent {correspondent}")

    # Update the document title, tags, and correspondent
    if not dry_run:
        update_document_title_tags_and_correspondent(sess, doc_pk, full_title, tags, correspondent, created_date, paperless_url)
    
    # Check if the custom field 'summary' exists, create if it doesn't
    summary_field_id = get_or_create_custom_field(sess, "summary", paperless_url)
    if not summary_field_id:
        logging.error(f"could not create or retrieve custom field 'summary' for document {doc_pk}")
        return

    # Update the document with the generated summary
    if not dry_run:
        update_document_with_custom_fields(sess, doc_pk, summary_field_id, summary, paperless_url)


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
