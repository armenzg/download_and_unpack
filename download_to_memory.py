#! /usr/bin/env python
# Code based on http://stackoverflow.com/a/15353312
import StringIO
import gzip
import time
import urllib2

from parser import parse_args

options = parse_args()
filename = 'file'

times = []

for i in range(0, 50):
    start = time.time()
    response = urllib2.urlopen(options.url)
    compressedFile = StringIO.StringIO()
    compressedFile.write(response.read())

    # Set the file's current position to the beginning
    # of the file so that gzip.GzipFile can read
    # its contents from the top.
    compressedFile.seek(0)

    decompressedFile = gzip.GzipFile(fileobj=compressedFile, mode='rb')

    with open(filename, 'w') as outfile:
        outfile.write(decompressedFile.read())

    times.append(time.time() - start)

print "Average {}".format(reduce(lambda x, y: x + y, times) / float(len(times)))
