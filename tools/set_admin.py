#!/usr/bin/env python3
import argparse
import os
import json
import hashlib
import binascii
import getpass

def hash_password(password, salt=None, iterations=100000):
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=32)
    return binascii.hexlify(salt).decode('ascii'), binascii.hexlify(dk).decode('ascii')

def main():
    p = argparse.ArgumentParser(description='Create or rotate admin credentials (writes admin/creds.json)')
    p.add_argument('--username', required=True)
    p.add_argument('--password', help='Password (will prompt if omitted)')
    p.add_argument('--iterations', type=int, default=100000)
    args = p.parse_args()

    pwd = args.password
    if not pwd:
        pwd = getpass.getpass('Password: ')
        pwd2 = getpass.getpass('Confirm: ')
        if pwd != pwd2:
            print('Passwords do not match')
            return

    salt_hex, hash_hex = hash_password(pwd, None, args.iterations)

    repo_root = os.path.dirname(os.path.dirname(__file__))
    creds_path = os.path.join(repo_root, 'admin', 'creds.json')
    data = {
        'username': args.username,
        'salt': salt_hex,
        'hash': hash_hex,
        'iterations': args.iterations
    }
    with open(creds_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print('Wrote', creds_path)

if __name__ == '__main__':
    main()
