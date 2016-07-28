#! /usr/bin/env python
# Code based on http://stackoverflow.com/a/15353312
import StringIO
import gzip
import os
import tarfile
import time
import urllib2

from parser import parse_args

options = parse_args()
filename = 'file'
times = []

for i in range(0, 50):
    start = time.time()

    # Code from mozharness/base/script.py _download_file & unpack
    # f_length = None
    f = urllib2.urlopen(options.url)

    # if f.info().get('content-length') is not None:
    #    f_length = int(f.info()['content-length'])
    #    got_length = 0

    local_file = open(filename, 'wb')

    while True:
        block = f.read(1024 ** 2)
        if not block:
        #    if f_length is not None and got_length != f_length:
        #        raise urllib2.URLError("Download incomplete; content-length was %d, but only received %d" % (f_length, got_length))
            break
        local_file.write(block)
        # if f_length is not None:
        #    got_length += len(block)
    local_file.close()

    end = time.time()
    times.append(end - start)

print "Average {}".format(reduce(lambda x, y: x + y, times) / float(len(times)))
