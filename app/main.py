#!/usr/bin/env python3
import json
import logging
import os
import sys
from datetime import datetime

import requests
from openai import OpenAI
from cfg import (OPENAI_API_KEY, OPENAPI_MODEL, PAPERLESS_API_KEY, PAPERLESS_URL, PROMPT, OPENAI_BASEURL, TIMEOUT)
from helpers import make_request, strtobool, get_character_limit
from tags import get_or_create_tags
from correspondents import get_or_create_correspondent
from custom_fields import get_or_create_custom_field
from document_type import get_or_create_document_type

def check_args(doc_pk):
    """Verifies that all required arguments and environment variables are present."""
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

def update_document_created_date_if_earlier(sess, doc_pk, openai_created_date, paperless_created_date, paperless_url):
    """Updates the document's created date if the OpenAI date is earlier."""
    if paperless_created_date:
        # Compare dates
        openai_date = datetime.strptime(openai_created_date, '%Y-%m-%d')
        paperless_date = datetime.strptime(paperless_created_date, '%Y-%m-%d')
        if openai_date < paperless_date:
            logging.info(f"OpenAI created_date {openai_created_date} is earlier than Paperless date {paperless_created_date}. Updating Paperless.")
            update_document_created_date(sess, doc_pk, openai_created_date, paperless_url)
        else:
            logging.info(f"Paperless created_date {paperless_created_date} is earlier. No update needed.")
    else:
        # If no created_date in Paperless, use the OpenAI date
        logging.info(f"No created_date in Paperless. Setting OpenAI created_date {openai_created_date}.")
        update_document_created_date(sess, doc_pk, openai_created_date, paperless_url)

def update_document_created_date(sess, doc_pk, created_date, paperless_url):
    """Updates the document's created_date in Paperless."""
    url = paperless_url + f"/api/documents/{doc_pk}/"
    body = {"created_date": created_date}
    resp = make_request(sess, url, "PATCH", body=body)
    if not resp:
        logging.error(f"could not update document {doc_pk} with created_date {created_date}")
    else:
        logging.info(f"updated document {doc_pk} with created_date {created_date}")

def query_openai(model, messages, openai_key, openai_base_url, **kwargs):
    """Queries OpenAI to generate title, tags, correspondent, and created_date."""
    client = OpenAI(api_key=openai_key, base_url=openai_base_url)
    args_to_remove = ['mock', 'completion_tokens']
    for arg in args_to_remove:
        if arg in kwargs:
            del kwargs[arg]
    return client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        **kwargs
    )

def generate_title_tags_correspondent_and_type(content, openai_model, openai_key, openai_base_url):
    """Generates title, tags, correspondent, document_type, and extracts the most relevant date from the content."""
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

def parse_response(response):
    """Parses the response from OpenAI to extract title, explanation, tags, correspondent, created_date, document_type, and summary."""
    try:
        data = json.loads(response)
    except:
        return None, None, None, None, None, None, None
    return data['title'], data.get('explanation', ""), data.get('tags', []), data.get('correspondent', ""), data.get('created_date', ""), data.get('document_type', ""), data.get('summary', "")

def update_document_title_tags_correspondent_and_type(sess, doc_pk, title, tags, correspondent, document_type, paperless_url):
    """Updates the document with title, tags, correspondent, and document_type."""
    
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

    # Get or create document_type and its ID
    document_type_id = get_or_create_document_type(sess, document_type, paperless_url)
    if not document_type_id:
        logging.error(f"could not retrieve or create document_type for document {doc_pk}")
        return

    # Update the document with the title, tags, correspondent, and document type
    url = paperless_url + f"/api/documents/{doc_pk}/"
    body = {
        "title": title,
        "tags": tag_ids,
        "correspondent": correspondent_id,
        "document_type": document_type_id
    }
    resp = make_request(sess, url, "PATCH", body=body)
    if not resp:
        logging.error(f"could not update document {doc_pk} with title, tags, correspondent, and document_type")
    else:
        logging.info(f"updated document {doc_pk} with title {title}, tags {tags}, correspondent {correspondent}, and document_type {document_type}")

def update_document_with_custom_fields(sess, doc_pk, custom_field_id, summary_value, paperless_url):
    """Updates the document with the generated summary in the custom field."""
    url = paperless_url + f"/api/documents/{doc_pk}/"
    body = {
        "custom_fields": [{"field": custom_field_id, "value": summary_value}]
    }
    resp = make_request(sess, url, "PATCH", body=body)
    if not resp:
        logging.error(f"could not update document {doc_pk} with custom field {custom_field_id} and value {summary_value}")
    else:
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
    """Processes a single document: generates a title, tags, correspondent, document_type, summary, and handles created_date logic."""
    
    # Get document information, including created date
    doc_info = get_single_document(sess, doc_pk, paperless_url)
    if not doc_info:
        logging.error(f"could not retrieve document info for document {doc_pk}")
        return

    # Call OpenAI to generate title, tags, correspondent, created_date, document_type, and summary
    response = generate_title_tags_correspondent_and_type(doc_contents, openai_model, openai_key, openai_base_url)
    if not response:
        logging.error(f"could not generate title, tags, correspondent, document_type, or summary for document {doc_pk}")
        return
    
    # Parse response from OpenAI
    title, explain, tags, correspondent, openai_created_date, document_type, summary = parse_response(response)
    if not title or not summary:
        logging.error(f"could not parse response for document {doc_pk}: {response}")
        return
    
    # Use the title from OpenAI directly, without adding the date
    logging.info(f"will update document {doc_pk} title from {doc_title} to: {title} because {explain}, with tags {tags}, correspondent {correspondent}, document type {document_type}, and summary {summary}")

    # Update the document title, tags, correspondent, and document type
    if not dry_run:
        update_document_title_tags_correspondent_and_type(sess, doc_pk, title, tags, correspondent, document_type, paperless_url)
    
    # Handle the created_date logic
    paperless_created_date = get_document_created_date(doc_info)
    if openai_created_date:
        update_document_created_date_if_earlier(sess, doc_pk, openai_created_date, paperless_created_date, paperless_url)

    # Check if the custom field 'summary' exists, create if it doesn't
    summary_field_id = get_or_create_custom_field(sess, "summary", paperless_url)
    if not summary_field_id:
        logging.error(f"could not create or retrieve custom field 'summary' for document {doc_pk}")
        return

    # Update the document with the generated summary
    if not dry_run:
        update_document_with_custom_fields(sess, doc_pk, summary_field_id, summary, paperless_url)

def get_single_document(sess, doc_pk, paperless_url):
    """Retrieves the content of a single document."""
    url = paperless_url + f"/api/documents/{doc_pk}/"
    return make_request(sess, url, "GET")

def run_for_document(doc_pk):
    """Runs the process for a single document."""
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
            DRY_RUN
        )

def set_auth_tokens(session: requests.Session, api_key):
    """Sets authentication tokens for the session."""
    session.headers.update(
        {"Authorization": f"Token {api_key}"}
    )

if __name__ == '__main__':
    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=LOGLEVEL)
    DRY_RUN = strtobool(os.getenv("DRY_RUN", "false"))
    if DRY_RUN:
        logging.info("DRY_RUN ENABLED")
    run_for_document(os.getenv("DOCUMENT_ID"))
