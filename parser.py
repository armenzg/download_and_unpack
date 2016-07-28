from argparse import ArgumentParser

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--url", dest="url", required=True, help='File to download and unpack.')
    return parser.parse_args()
