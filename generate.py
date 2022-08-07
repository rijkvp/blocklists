import os, datetime, requests, re, logging, asyncio, concurrent.futures, json

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)

SOURCE_DIR = "src"
DEST_DIR = "dist"
STMT_OPERATOR = "!!"

def download_webpage(url):
    res = requests.get(url)
    logging.info("downloading {}".format(url))
    if res.ok:
        return res.text
    else:
        logging.warning("failed to download {}, {}, {}".format(url, res.status_code, res.text))
        return None

def download_webpages(urls):
    pages = []
    with  concurrent.futures.ThreadPoolExecutor(20) as executor:
        for result in executor.map(download_webpage, urls):
            if result != None:
                pages.append(result)
    logging.info("downloaded {}/{} webpages".format(len(pages), len(urls)))
    return pages

# Extract hostnames from blocklists
def extract_hostnames(lines):
    hostnames = []
    for line in lines:
        line = line.strip()
        if not (line == "" or line.startswith("!") or line.startswith("#")):
            matched = re.search("[\w\d-]+(\.[\w\d]+)+", line)
            if matched:
                hostnames.append(matched.group())
            else:
                logging.warning("failed to extract: '{}'".format(line))
    return hostnames

def apply_templates(inputs, templates):
    result = ""
    for template in templates:
        for input in inputs:
            result += template.format(input) + "\n"
    return result

for filename in os.listdir(SOURCE_DIR):
    path = os.path.join(SOURCE_DIR, filename)

    if not os.path.isfile(path):
        continue

    meta = {}
    sources = []
    templates = []
    hostnames = []
    result = ""
    with open(path, "r") as f:
        logging.info("generating source {}".format(path))
        contents = f.readlines()
        for line in contents:
            line = line.strip()
            if line == "":
                continue
            elif line.startswith(STMT_OPERATOR):
                stmt, input = line.split(" ", 1)
                stmt = stmt[2:]
                if stmt == "meta":
                    key, val = input.split(" ", 1)
                    meta[key] = val
                elif stmt == "src":
                    sources.append(input.strip())
                elif stmt == "tmpl":
                    templates.append(input.strip())
                elif stmt == "add":
                    hostname = input.strip()
                    if hostname[0] == "@":
                        # Invidious instances API
                        if hostname[1:] == "invidious":
                            logging.info("downloading list of invidious instances..")
                            res = requests.get("https://api.invidious.io/instances.json?sort_by=health")
                            if res.ok:
                                json = json.loads(res.text)
                                for item in json:
                                    if item[1]['type'] == "https":
                                        hostnames.append(item[0])
                            else:
                                logging.warning("failed to download invidious instances {}, {}, {}".format(url, res.status_code, res.text))
                    else:
                        hostnames.append(hostname)
                else:
                    logging.error("unkown statement {}".format(stmt))

            elif not line.startswith("!"):
                result += line + "\n"

    # Merge blocklists
    if len(sources) > 0 or len(hostnames) > 0:
        if len(sources) > 0:
            lists = download_webpages(sources)
            for text in lists:
                lines = text.split("\n")
                list_hostnames = extract_hostnames(lines)
                hostnames.extend(list_hostnames)

        # Remove duplicates
        items = []
        [items.append(x) for x in hostnames if x not in items]
        items.sort()
        logging.info("reduced duplicates from {} to {} hosts".format(len(hostnames), len(items)))

        # Templates
        result += apply_templates(items, templates)

    # Add generated & expires metadata
    meta["Generated"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    meta["Expires"] = "1 day"

    # Generate metadata
    header = ""
    for key, val in meta.items():
        header += "! {}: {}\n".format(key, val)
    result = header + result

    # Write output
    os.makedirs(DEST_DIR, exist_ok=True)
    dest_path = os.path.join(DEST_DIR, filename + ".txt")
    with open(dest_path, "w") as f:
        logging.info("saving output to {}".format(str(dest_path)))
        f.write(result)
