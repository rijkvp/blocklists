import os, datetime, requests, re, logging

logging.basicConfig(level=logging.DEBUG)

SOURCE_DIR = "src"
DEST_DIR = "dist"
STMT_OPERATOR = "!!"

# Removes comments and whitespace
def filter_blocklist(input):
    result = ""
    for line in input.split("\n"):
        line = line.strip()
        if not (line == "" or line.startswith("!") or line.startswith("#")):
            result += line + "\n"
    return result

# Removes ublacklist syntax, extracts hostnames with regex
def filter_ublacklist(input):
    result = ""
    for line in input.split("\n"):
        line = line.strip()
        matched = re.search("[\w\d-]+(\.[\w\d]+)+", line)
        if matched:
            result += matched.group() + "\n"
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
                    format, url = input.split(" ", 1)
                    res = requests.get(url)
                    logging.info("downloading {}".format(url))
                    if res.ok:
                        if format == "hosts":
                            result += filter_blocklist(res.text)
                        elif format == "ublacklist":
                            result += filter_ublacklist(filter_blocklist(res.text))
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
