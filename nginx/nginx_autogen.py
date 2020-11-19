import argparse
import os
import pathlib

parser = argparse.ArgumentParser()

parser.add_argument('in_file', help='The file(s) that you would like to use as input')
parser.add_argument("-o", "--out", nargs="?", default="/etc/nginx/generated", help='The output directory where sites/ and streams/ will go, defaults to /etc/nginx/generated')
parser.add_argument("-d", "--domain", nargs="?", default="clicksminuteper.net", help='The default TLD, defaults to clicksminuteper.net')
parser.add_argument("-s", "--ssl_dir", "--ssl", nargs="?", default="/etc/letsencrypt/live/{tld}", help='The location of your SSL certificates, you can use {tld} to specify the default TLD or {domain} to specify the main domain')

args = parser.parse_args()

site_template = """server {{
    server_name {domains} {www_domains};
    access_log /var/log/nginx/{primary}-access.log;
    error_log /var/log/nginx/{primary}-error.log;

    location / {{
        proxy_pass http://{host}:{port};
    }}

    listen [::]:443 ssl;
    listen 443 ssl;

    ssl_certificate {ssl_dir}/fullchain.pem;
    ssl_certificate_key {ssl_dir}/privkey.pem;

    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}}
"""
stream_upstream_template = """
upstream stream_{port} {{
    server {host}:{upstream_port};
}}
"""
stream_server_template = """
server {{
    listen 0.0.0.0:{port};
    proxy_pass stream_{port};
}}
"""


try:
  with open(args.in_file, "r") as in_file:
    in_data = in_file.readlines()
except (IndexError, FileNotFoundError):
  print("You must enter a valid input file")
  sys.exit(1)

pathlib.Path(os.path.join(args.out or ".", "sites")).mkdir(parents=True, exist_ok=True)
pathlib.Path(os.path.join(args.out or ".", "streams")).mkdir(parents=True, exist_ok=True)

print("Proxying and streaming sites, please remember that this will not delete any files, only overwrite existing ones. Any files you no longer need must be deleted manually")

for line in in_data:
    parts = [item.strip() for item in line.split(" ")]
    if parts[0] == "stream":
        host, _, upstream_port = parts[1].partition(":")
        if not host:
            print(f"Warning: you must supply a host to stream from ({line})")
            continue
        if len(parts) > 2 and parts[2] == "to":
            try:
                port = parts[3].split(",")
            except IndexError:
                print(f"Warning: you must supply a port to stream to after specifying 'to' ({line})")
                continue
        else:
            port = (upstream_port,)
        print(f"Streaming {host}:{upstream_port}. Please remember to run 'ufw allow {{port}}' for each specified port (or another command to unrestrict the port if your firewall is not ufw)")
        stream_text = stream_upstream_template.format(port=port[0], host=host, upstream_port=upstream_port)
        for individual_port in port:
            stream_text += "\n" + stream_server_template.format(port=individual_port, host=host, upstream_port=upstream_port)
        with open(os.path.join(args.out or '.', 'streams', port[0]), "w") as out_file:
            out_file.write(stream_text)
    elif parts[0] == "proxy" and parts[2] == "to":
        domains = [domain if "." in domain else f"{domain}.{args.domain}" for domain in parts[3].split(",")]
        part1, _, part2 = parts[1].partition(":")
        port = part2 or part1
        host = part1 if part2 else "127.0.0.1"
        print(f"Proxying {host}:{port}")
        site_text = site_template.format(
            domains=' '.join(domains),
            primary=domains[0],
            www_domains=' '.join(f'www.{domain}' for domain in domains),
            host=host,
            port=port,
            ssl_dir=args.ssl_dir.format(tld=args.domain, domain=domains[0])
        )
        with open(os.path.join(args.out or '.', 'sites', domains[0]), "w") as out_file:
            out_file.write(site_text)

print("Reconfiguration complete, please remember to restart NGINX")