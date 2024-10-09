import logging
from helpers import make_request

def generate_random_hex_color():
    """Generates a random hex color string."""
    import random
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def create_new_tag(sess, tag_name, paperless_url, owner_id):
    """Creates a new tag in Paperless and returns its ID."""
    url = paperless_url + "/api/tags/"
    owner_id_or_empty = owner_id or ''

    body = {
        "name": tag_name,
        "color": generate_random_hex_color(),
        "owner": owner_id_or_empty  # Owner is optional
    }
        
    response = make_request(sess, url, "POST", body=body)
    if not response:
        logging.error(f"could not create tag {tag_name}")
        return None
    logging.info(f"created new tag: {tag_name} with color {body['color']}")
    return response['id']

def get_existing_tag(sess, tag_name, paperless_url):
    """Checks if a tag with the exact name already exists."""
    url = paperless_url + f"/api/tags/?name__iexact={tag_name}"
    response = make_request(sess, url, "GET")
    if not response:
        logging.error(f"could not retrieve tag {tag_name}")
        return None
    if len(response['results']) > 0:
        tag = response['results'][0]
        logging.info(f"tag {tag_name} already exists with id {tag['id']}")
        return tag['id']
    return None

def get_or_create_tags(sess, tags, paperless_url, owner_id=None):
    """Checks if tags exist; if not, creates them with random colors. Returns list of tag IDs."""
    tag_ids = []
    
    for tag in tags:
        tag_id = get_existing_tag(sess, tag, paperless_url)
        if tag_id:
            tag_ids.append(tag_id)
        else:
            new_tag_id = create_new_tag(sess, tag, paperless_url, owner_id)
            if new_tag_id:
                tag_ids.append(new_tag_id)
    
    return tag_ids