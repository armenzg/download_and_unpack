#! /usr/bin/env python
import fnmatch
import functools
import gzip
import itertools
import logging
import os
import sys
import tarfile
import time
import urllib2
import urlparse
import zipfile
import zlib

from argparse import ArgumentParser
from cStringIO import StringIO

CWD = os.path.dirname(os.path.realpath(__file__))
LOG = logging.getLogger()


def main():
    options = parse_args()
    level = logging.DEBUG if options.debug else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=level)
    download_unpack_time(
        options.url,
        options.times,
        extract_to=options.extract_to,
        extract_dirs=options.extract_dirs
    )


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--url", dest="url",
                        help='File to download and unpack.')
    parser.add_argument("--times", dest="times", default=1, type=int,
                        help='How many times to test download a file.')
    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")
    parser.add_argument("--extract-to", dest="extract_to",
                        help='Where to extract the files.')
    parser.add_argument("--extract-dirs", dest="extract_dirs",
                        action="append",
                        help='Which directories to extract from a compressed file.')
    return parser.parse_args()


def unzip(response, extract_to='.', extract_dirs='*'):
    def _filter_entries(namelist):
        """Filter entries of the archive based on the specified list of to extract dirs."""
        filter_partial = functools.partial(fnmatch.filter, namelist)
        for entry in itertools.chain(*map(filter_partial, extract_dirs or ['*'])):
            yield entry

    LOG.info('Using ZipFile to extract {} to {} from {}'.format(
        ', '.join(extract_dirs),
        extract_to,
        response.url,
    ))
    compressed_file = StringIO(response.read())
    try:
        with zipfile.ZipFile(compressed_file) as bundle:
            entries = _filter_entries(bundle.namelist())

            for entry in entries:
                bundle.extract(entry, path=extract_to)

                # ZipFile doesn't preserve permissions during extraction:
                # http://bugs.python.org/issue15795
                fname = os.path.realpath(os.path.join(extract_to, entry))
                mode = bundle.getinfo(entry).external_attr >> 16 & 0x1FF
                # Only set permissions if attributes are available. Otherwise all
                # permissions will be removed eg. on Windows.
                if mode:
                    os.chmod(fname, mode)

    except zipfile.BadZipfile as e:
        print '{} {}'.format(e.message, filename)


def deflate(response, mode, extract_to='.'):
    LOG.info('Using TarFile to extract to {} with mode {} from {}'.format(
        extract_to,
        mode,
        response.url,
    ))
    compressed_file = StringIO(response.read())
    t = tarfile.open(fileobj=compressed_file, mode=mode)
    t.extractall(path=extract_to)


def maybe_gzip(response):
    # XXX: We need to write file to disk
    content_encoding = response.headers.get('Content-Encoding')

    if content_encoding == 'gzip':
        # XXX: Fix comment later
        LOG.debug('Possibly ungzipping a txt file...')
        compressed_file = StringIO(response.read())
        data = gzip.GzipFile(fileobj=compressed_file).read()

    elif not content_encoding:
        LOG.debug('No content encoding')
        data = response.read()

    else:
        raise Exception('We have not yet added support for "{}" encoding'.format(content_encoding))


EXTENSION_TO_MIMETYPE = {
    'bz2': 'application/x-bzip2',
    'gz':  'application/x-gzip',
    'tar': 'application/x-tar',
    'txt': 'text/plain',
    'zip': 'application/zip',
}
MIMETYPES = {
    'application/x-bzip2': {
        'function': deflate,
        'kwargs': {'mode': 'r:bz2'},
    },
    'application/x-gzip': {
        'function': deflate,
        'kwargs': {'mode': 'r:gz'},
    },
    'application/x-tar': {
        'function': deflate,
        'kwargs': {'mode': 'r'},
    },
    'application/zip': {
        'function': unzip,
    },
    'text/plain': {
        'function': maybe_gzip,
    },
}


def download_unpack(fd, **kwargs):
    parsed_fd = urlparse.urlparse(fd)

    # In case we're referrencing a file without file://
    if parsed_fd.scheme == '':
        if not os.path.isfile(fd):
            raise IOError('Could not find file to extract: {}'.format(fd))

        fd = 'file://%s' % os.path.abspath(fd)
        parsed_fd = urlparse.urlparse(fd)

    request = urllib2.Request(fd)
    request.add_header('Accept-encoding', 'gzip')
    response = urllib2.urlopen(request)

    if parsed_fd.scheme == 'file':
        filename = fd.split('/')[-1]
        # XXX: bz2/gz instead of tar.{bz2/gz}
        extension = filename[filename.rfind('.')+1:]
        mimetype = EXTENSION_TO_MIMETYPE[extension]
    else:
        mimetype = response.headers.type

    # This line gives too much information, however, it is good to have around
    # LOG.debug(response.headers)
    LOG.debug('Url:\t\t\t{}'.format(fd))
    LOG.debug('Mimetype:\t\t{}'.format(mimetype))
    LOG.debug('Content-Encoding\t{}'.format(response.headers.get('Content-Encoding')))

    function = MIMETYPES[mimetype]['function']
    # Remove kwargs that have None as a value
    kwargs = dict((k, v) for k, v in kwargs.iteritems() if v)
    kwargs.update(MIMETYPES[mimetype].get('kwargs', {}))

    function(response=response, **kwargs)


def download_unpack_time(url, times, **kwargs):
    timings = []
    for i in range(0, times):
        start = time.time()
        download_unpack(url, **kwargs)
        timings.append(time.time() - start)

    LOG.info(
        "Average {}  {}".format(
            round(reduce(lambda x, y: x + y, timings) / float(len(timings)), 4),
            url
        )
    )


if __name__ == "__main__":
    main()
