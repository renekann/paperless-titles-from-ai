import logging
from helpers import make_request

def get_existing_document_type(sess, document_type_name, paperless_url):
    """Checks if a document_type with the exact name already exists."""
    url = paperless_url + f"/api/document_types/?name__iexact={document_type_name}"
    response = make_request(sess, url, "GET")
    if not response:
        logging.error(f"could not retrieve document_type {document_type_name}")
        return None
    if len(response['results']) > 0:
        document_type = response['results'][0]
        logging.info(f"document_type {document_type_name} already exists with id {document_type['id']}")
        return document_type['id']
    return None

def create_new_document_type(sess, document_type_name, paperless_url):
    """Creates a new document_type in Paperless and returns its ID."""
    url = paperless_url + "/api/document_types/"
    body = {
        "name": document_type_name
    }
    response = make_request(sess, url, "POST", body=body)
    if not response:
        logging.error(f"could not create document_type {document_type_name}")
        return None
    logging.info(f"created new document_type: {document_type_name}")
    return response['id']

def get_or_create_document_type(sess, document_type, paperless_url):
    """Checks if a document_type exists; if not, creates it and returns the document_type ID."""
    # Check if document_type exists by name
    document_type_id = get_existing_document_type(sess, document_type, paperless_url)
    
    if document_type_id:
        return document_type_id
    else:
        # Create a new document_type if it does not exist
        new_document_type_id = create_new_document_type(sess, document_type, paperless_url)
        if new_document_type_id:
            return new_document_type_id
        else:
            logging.error(f"could not create or find document_type {document_type}")
            return None