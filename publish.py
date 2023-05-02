import requests
import argparse
import subprocess
from dotenv import load_dotenv
import os
import markdown
from bs4 import BeautifulSoup

### ADD MEDIUM INTEGRATION TOKEN HERE ###
load_dotenv()
TOKEN = os.getenv('MEDIUM_TOKEN')

def get_headers(token):
    headers = {
        "Accept":	"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding"	:"gzip, deflate, br",
        "Accept-Language"	:"en-US,en;q=0.5",
        "Connection"	:"keep-alive",
        "Host"	:"api.medium.com",
        "Authorization": "Bearer {}".format(token),
        "Upgrade-Insecure-Requests":	"1",
        "User-Agent":	"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
    }
    return headers

def read_file(filepath):
    '''reads file from input filepath and returns a dict with the file content and contentFormat for the publish payload'''
    f = open(filepath, 'r')
    content = f.read()
    if not f.closed: f.close()

    if filepath.find('.') < 0:
        file_ext = ""
    else:
        file_ext = filepath[filepath.find(".")+1:]
    if file_ext == "md": file_ext = "markdown"
    return {"content": content, "contentFormat": file_ext}

def prep_data(args):
    '''prepares payload to publish post'''
    data = {
        "title": args['title'],
    }
    data = {**data, **read_file(args['filepath'])}
    if args['tags']:
        data['tags'] = [t.strip() for t in args['tags'].split(',')]
    data['publishStatus'] = 'draft'
    if args['pub']:
        data['publishStatus'] = args['pub']
    return data

def get_author_id(token):
    '''uses the /me medium api endpoint to get the user's author id'''
    response = requests.get("https://api.medium.com/v1/me", headers=get_headers(token), params={"Authorization": "Bearer {}".format(token)})
    if response.status_code == 200:
        return response.json()['data']['id']
    else:
        print(f"Get Author ID Error:")
        print(response)
    return None

def extract_images(content: str):
    """
    Extract images
    :param content: The post content
    :return: A list of images
    """
    output = markdown.markdown(content)
    soup = BeautifulSoup(output, "html.parser")
    imgs_extracted_html = soup.find_all("img")
    imgs_extracted_list = []
    for image in imgs_extracted_html:
        imgs_extracted_list.append(image['src'])
    return imgs_extracted_list

def publish_image(image_path,
                  headers):
    """
    Publish a single image on the medium
    :param image_path: Path of the image
    :param headers: the medium headers
    :return: The published path
    """
    # Open image
    with open(image_path, "rb") as f:
        filename = image_path.split(".")[0]
        extension = image_path.split(".")[-1]
        content_type = f"image/{extension}"
        files = {"image": (filename, f, content_type)}
        url = "https://api.medium.com/v1/images"
        response = requests.request("post", url, headers=headers, files=files)
        if 200 <= response.status_code < 300:
            json = response.json()
            try:
                return json["data"]["url"]
            except KeyError:
                return json

def post_article(data,
                 base_path: str):
    """
    Posts an article to medium with the input payload
    :param data: The content data in json
    :param token: The medium token
    :param base_path: the images base path
    :return: Post Url
    """
    headers = get_headers(TOKEN)
    images_path = extract_images(data["content"])
    for image_path in images_path:
        new_url = publish_image(f"{base_path}/{image_path}", headers)
        if new_url is not None:
            # Put the url instead of the original images
            data["content"] = data["content"].replace(image_path, new_url)
    author_id = get_author_id(TOKEN)
    url = f"https://api.medium.com/v1/users/{author_id}/posts"
    response = requests.request("post", url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        response_json = response.json()
        # get the URL of the uploaded post
        medium_post_url = response_json["data"]["url"]
        return medium_post_url
    else:
        print(response.status_code)
        print(response)
    return None

def copy_to_clipboard(to_copy):
    '''utility function to copy string to clipboard'''
    if not to_copy: return
    process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
    process.communicate(to_copy.encode('utf-8'))

if __name__ == "__main__":
    # initialise parser
    parser = argparse.ArgumentParser()

    # add compulsory arguments
    parser.add_argument('filepath') # positional argument
    parser.add_argument('-t', '--title', required=True, help="title of post", type=str) # named argument

    # add compulsory arguments
    parser.add_argument('-a', '--tags', required=False, help="tags, separated by ,", type=str)
    parser.add_argument('-p', '--pub', required=False, help="publish status, one of draft/unlisted/public, defaults to draft", type=str, choices=["public", "unlisted", "draft"])

    # read arguments
    args = parser.parse_args()
    filepath = args.filepath
    data = prep_data(vars(args))
    post_url = post_article(data, base_path = "/".join(filepath.split("/")[:-1]))
    copy_to_clipboard(post_url) # copy url to clipboard if any
    print(post_url)
