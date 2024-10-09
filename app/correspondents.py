import logging
from helpers import make_request

def get_existing_correspondent(sess, correspondent_name, paperless_url):
    """Checks if a correspondent with the exact name already exists."""
    url = paperless_url + f"/api/correspondents/?name__iexact={correspondent_name}"
    response = make_request(sess, url, "GET")
    if not response:
        logging.error(f"could not retrieve correspondent {correspondent_name}")
        return None
    if len(response['results']) > 0:
        correspondent = response['results'][0]
        logging.info(f"correspondent {correspondent_name} already exists with id {correspondent['id']}")
        return correspondent['id']
    return None

def create_new_correspondent(sess, correspondent_name, paperless_url, owner_id):
    """Creates a new correspondent in Paperless and returns its ID."""
    url = paperless_url + "/api/correspondents/"
    owner_id_or_empty = owner_id or ''
    body = {
        "name": correspondent_name,
        "owner": owner_id_or_empty
    }

    response = make_request(sess, url, "POST", body=body)
    if not response:
        logging.error(f"could not create correspondent {correspondent_name}")
        return None
    logging.info(f"created new correspondent: {correspondent_name}")
    return response['id']

def get_or_create_correspondent(sess, correspondent_name, paperless_url, owner_id=None):
    """Checks if a correspondent exists; if not, creates it and returns the correspondent ID."""
    # Check if correspondent exists by name
    correspondent_id = get_existing_correspondent(sess, correspondent_name, paperless_url)
    
    if correspondent_id:
        return correspondent_id
    else:
        # Create a new correspondent if it does not exist
        new_correspondent_id = create_new_correspondent(sess, correspondent_name, paperless_url, owner_id)
        if new_correspondent_id:
            return new_correspondent_id
        else:
            logging.error(f"could not create or find correspondent {correspondent_name}")
            return None