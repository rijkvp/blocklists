import os, datetime, requests, re, logging

logging.basicConfig(level=logging.DEBUG)

SOURCE_DIR = "src"
DEST_DIR = "dist"
STMT_OPERATOR = "!!"

# Removes comments and whitespace
def filter_blocklist(lines):
    result = []
    for line in lines:
        line = line.strip()
        if not (line == "" or line.startswith("!") or line.startswith("#")):
            result.append(line)
    return result

# Removes ublacklist syntax, extracts hostnames with regex
def filter_ublacklist(lines):
    result = []
    for line in lines:
        matched = re.search("[\w\d-]+(\.[\w\d]+)+", line)
        if matched:
            result.append(matched.group())
    return result

def apply_templates(lines, templates):
    result = ""
    for line in lines:
        for template in templates:
            result += template.format(line) + "\n"
    return result
        

for filename in os.listdir(SOURCE_DIR):
    path = os.path.join(SOURCE_DIR, filename)

    if not os.path.isfile(path):
        continue

    meta = {}
    result = ""
    with open(path, "r") as f:
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
                    format, url, templates = input.split(" ", 2)
                    res = requests.get(url)
                    templates = templates.split(" ")
                    templates = [t for t in templates if f != '']
                    logging.info("downloading {}".format(url))
                    if res.ok:
                        lines = res.text.split("\n")
                        if format == "hosts":
                            lines = filter_blocklist(lines)
                            result += apply_templates(lines, templates)
                        elif format == "ublacklist":
                            lines = filter_ublacklist(filter_blocklist(lines))
                            result += apply_templates(lines, templates)
                        else:
                            logging.error("unkown source format {}".format(format))
                    else:
                        logging.warning("failed to download {}, {}, {}".format(url, res.status_code, res.text))
                else:
                    logging.error("unkown statement {}".format(stmt))
                    
            elif not line.startswith("!"):
                result += line + "\n"

    # Remove duplicates
    result_lines = result.split("\n")
    logging.info("removing duplicates from {} lines".format(len(result_lines)))
    items = []
    [items.append(x) for x in result_lines if x not in items]
    items.sort()
    result = "\n".join(items)
    logging.info("reduced duplicates from {} to {} lines".format(len(result_lines), len(items)))


    # Add generated metadata
    meta["Generated"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Add metadata
    header = ""
    for key, val in meta.items():
        header += "! {}: {}\n".format(key, val)
    result = header + result

    # Write output
    os.makedirs(DEST_DIR, exist_ok=True) 
    dest_path = os.path.join(DEST_DIR, filename + ".txt")
    with open(dest_path, "w") as f:
        logging.info("written {}".format(str(dest_path)))
        f.write(result)
