#! /usr/bin/env python
import os
import tarfile
import time
import urllib2
import zipfile
import zlib

from cStringIO import StringIO

from common import parse_args

cwd = os.path.dirname(os.path.realpath(__file__))


def ungzip(url):
    def _decompress_gzip_stream(fh):
        """Consume a file handle with gzip data and emit decompressed chunks."""

        # The |32 is magic to parse the gzip header
        d = zlib.decompressobj(zlib.MAX_WBITS|32)

        while True:
            # XXX: Where does this magical number come from?
            data = fh.read(262144)
            if not data:
                break

            yield d.decompress(data)

        yield d.flush()

    response = urllib2.urlopen(url)
    # XXX: We still need to untar
    filename = 'temp.txt'
    with open(filename, 'wb') as fh:
        for chunk in _decompress_gzip_stream(response):
            fh.write(chunk)


def unbz2(url):
    response = urllib2.urlopen(url)
    compressed_file = StringIO(response.read())
    t = tarfile.open(fileobj=compressed_file, mode='r:bz2')
    t.extractall()


def untar(url):
    response = urllib2.urlopen(url)
    compressed_file = StringIO(response.read())
    t = tarfile.open(fileobj=compressed_file, mode='r')
    t.extractall()


def unzip(url):
    response = urllib2.urlopen(url)
    compressed_file = StringIO(response.read())
    zf = zipfile.ZipFile(compressed_file)
    zf.extractall()


def download_unpack_time(url, times):
    timings = []
    for i in range(0, times):
        extension = url[url.find('.')+1:]
        start = time.time()
        try:
            EXTENSION_TO_METHOD[extension](url)
        except:
            print url
            raise

        timings.append(time.time() - start)

    print "Average {}\t{}".format(url, reduce(lambda x, y: x + y, timings) / float(len(timings)))


if __name__ == "__main__":
    options = parse_args()
    EXTENSION_TO_METHOD = {
        'tar': untar,
        'tar.bz2': unbz2,
        'tar.gz':  ungzip,
        'zip': unzip,
    }

    FILES = (
        'file://{}/archive.tar'.format(cwd),
        'file://{}/archive.tar.bz2'.format(cwd),
        'file://{}/archive.tar.gz'.format(cwd),
        'file://{}/archive.zip'.format(cwd),
    )

    for url in [options.url] if options.url else FILES:
        download_unpack_time(url, options.times)
