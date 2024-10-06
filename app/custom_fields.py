import logging
from helpers import make_request

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