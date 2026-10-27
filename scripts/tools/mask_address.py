#!/usr/bin/env python3
"""Print the masked forms of mail addresses: the value for identities and notes, and the form for snippets."""

import argparse

from scripts.lib.addresses import mask_address


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('addresses', nargs='+', metavar='ADDRESS', help='a mail address')
    args = parser.parse_args(argv)
    for address in args.addresses:
        print(address)
        print(f'  identities and notes: {mask_address(address)}')
        print(f'  snippets:             {mask_address(address, keep_domain=True)}')


if __name__ == '__main__':
    main()
