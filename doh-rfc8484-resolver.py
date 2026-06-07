#!/usr/bin/env python3
"""
DoH RFC 8484 Resolver
Reads domains from domain.ini, queries DoH servers from dns.ini,
saves resolved IPs to IP_<timestamp>.txt
"""

import argparse
import os
import socket
import struct
import sys
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DNS_HEADER_FMT = '!HHHHHH'


def read_lines(filename):
    path = os.path.join(SCRIPT_DIR, filename)
    lines = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                lines.append(line)
    return lines


def encode_dns_name(domain):
    encoded = b''
    for part in domain.rstrip('.').split('.'):
        encoded += struct.pack('!B', len(part)) + part.encode('ascii')
    encoded += b'\x00'
    return encoded


def build_dns_query(domain, qtype):
    id = 0
    flags = 0x0100
    qdcount = 1
    header = struct.pack(DNS_HEADER_FMT, id, flags, qdcount, 0, 0, 0)
    question = encode_dns_name(domain) + struct.pack('!HH', qtype, 1)
    return header + question


def parse_dns_response(data):
    id, flags, qdcount, ancount, nscount, arcount = struct.unpack(DNS_HEADER_FMT, data[:12])
    offset = 12

    for _ in range(qdcount):
        while offset < len(data) and data[offset] != 0:
            if data[offset] & 0xC0:
                offset += 2
                break
            offset += data[offset] + 1
        else:
            if offset < len(data) and data[offset] == 0:
                offset += 1
        offset += 4

    addresses = []
    for _ in range(ancount):
        if offset >= len(data):
            break
        if data[offset] & 0xC0:
            offset += 2
        else:
            while offset < len(data) and data[offset] != 0:
                offset += data[offset] + 1
            if offset < len(data):
                offset += 1

        if offset + 10 > len(data):
            break
        rtype, rclass, ttl, rdlength = struct.unpack('!HHIH', data[offset:offset+10])
        offset += 10

        if offset + rdlength > len(data):
            break

        if rtype == 1 and rdlength == 4:
            ip = socket.inet_ntop(socket.AF_INET, data[offset:offset+4])
            addresses.append(('A', ip))
        elif rtype == 28 and rdlength == 16:
            ip = socket.inet_ntop(socket.AF_INET6, data[offset:offset+16])
            addresses.append(('AAAA', ip))

        offset += rdlength

    return addresses


def query_doh(url, domain, qtype, timeout=10, verify_ssl=True):
    dns_query = build_dns_query(domain, qtype)

    headers = {
        'Content-Type': 'application/dns-message',
        'Accept': 'application/dns-message',
        'User-Agent': 'doh-rfc8484-resolver/1.0',
    }

    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, data=dns_query, headers=headers)
    resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
    raw = resp.read()
    resp.close()
    return parse_dns_response(raw)


def resolve_domain(domain, doh_servers, mode='auto', timeout=10):
    qtype_order = []
    if mode == 'ipv4':
        qtype_order = [1]
    elif mode == 'ipv6':
        qtype_order = [28]
    else:
        qtype_order = [1, 28]

    results = {}
    for qtype in qtype_order:
        for server in doh_servers:
            try:
                addrs = query_doh(server, domain, qtype, timeout)
                if addrs:
                    type_name = 'A' if qtype == 1 else 'AAAA'
                    results[type_name] = [ip for t, ip in addrs if t == type_name]
                    break
            except Exception as e:
                print(f"  -> {server} failed ({'A' if qtype==1 else 'AAAA'}): {e}", file=sys.stderr)
                continue
    return results


def main():
    parser = argparse.ArgumentParser(description='DoH RFC 8484 Resolver')
    parser.add_argument('-4', '--ipv4', action='store_true', help='Only resolve A records (IPv4)')
    parser.add_argument('-6', '--ipv6', action='store_true', help='Only resolve AAAA records (IPv6)')
    args = parser.parse_args()

    if args.ipv4 and args.ipv6:
        print("Error: Cannot specify both -4 and -6", file=sys.stderr)
        sys.exit(1)

    if args.ipv4:
        mode = 'ipv4'
    elif args.ipv6:
        mode = 'ipv6'
    else:
        mode = 'auto'

    domains = read_lines('domain.ini')
    doh_servers = read_lines('dns.ini')

    if not domains:
        print("Error: No domains found in domain.ini", file=sys.stderr)
        sys.exit(1)
    if not doh_servers:
        print("Error: No DoH servers found in dns.ini", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    output_file = os.path.join(SCRIPT_DIR, f'IP_{timestamp}.txt')

    print(f"Resolver mode: {mode}")
    print(f"DoH servers: {', '.join(doh_servers)}")
    print(f"Domains ({len(domains)}): {', '.join(domains)}")
    print(f"Output: {output_file}")
    print()

    with open(output_file, 'w', encoding='utf-8') as out:
        for domain in domains:
            print(f"[{domain}]")
            out.write(f"{domain}\n")
            results = resolve_domain(domain, doh_servers, mode)

            printed = False
            if 'A' in results:
                for ip in results['A']:
                    out.write(f"  A: {ip}\n")
                    print(f"  A: {ip}")
                    printed = True
            if 'AAAA' in results and (mode == 'ipv6' or (mode == 'auto' and 'A' not in results)):
                for ip in results['AAAA']:
                    out.write(f"  AAAA: {ip}\n")
                    print(f"  AAAA: {ip}")
                    printed = True
            if not printed:
                out.write("  (no records)\n")
                print("  (no records)")
            out.write("\n")
            print()

    print(f"Saved to {output_file}")


if __name__ == '__main__':
    main()
