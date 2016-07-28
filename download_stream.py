#! /usr/bin/env python
import time
import urllib2
import zlib

from parser import parse_args

options = parse_args()
filename = 'file'

def decompress_gzip_stream(fh):
    """Consume a file handle with gzip data and emit decompressed chunks."""

    # The |32 is magic to parse the gzip header
    d = zlib.decompressobj(zlib.MAX_WBITS|32)

    while True:
        data = fh.read(16384)
        if not data:
            break

        yield d.decompress(data)

    yield d.flush()

times = []

for i in range(0, 50):
    start = time.time()
    response = urllib2.urlopen(options.url)
    with open(filename, 'wb') as fh:
        for chunk in decompress_gzip_stream(response):
            fh.write(chunk)
    times.append(time.time() - start)

print "Average {}".format(reduce(lambda x, y: x + y, times) / float(len(times)))
