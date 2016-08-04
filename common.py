from argparse import ArgumentParser

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--url", dest="url",
                        help='File to download and unpack.')
    parser.add_argument("--times", dest="times", default=1, type=int,
                        help='How many times to test download a file.')
    return parser.parse_args()
