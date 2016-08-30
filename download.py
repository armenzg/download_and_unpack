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
        extract_to='.' if options.extract_to is None else options.extract_to,
        extract_dirs='*' if options.extract_dirs is None else options.extract_dirs,
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


# I'm making this module a class to make it easier to compare with Mozharness' code
class DownloadUnpack():
    def info(self, msg):
        LOG.info(msg)

    def debug(self, msg):
        LOG.debug(msg)

    def warning(self, msg):
        LOG.warning(msg)

    def _filter_entries(self, namelist, extract_dirs):
        """Filter entries of the archive based on the specified list of to extract dirs."""
        filter_partial = functools.partial(fnmatch.filter, namelist)
        entries = itertools.chain(*map(filter_partial, extract_dirs or ['*']))

        for entry in entries:
            yield entry

    def unzip(self, file_object, extract_to, extract_dirs='*', verbose=False):
        """This method allows to extract a zip file without writing to disk first.

        Args:
            file_object (object): Any file like object that is seekable.
            extract_to (str, optional): where to extract the compressed file.
            extract_dirs (list, optional): directories inside the archive file to extract.
                                           Defaults to '*'.
        """
        compressed_file = StringIO(file_object.read())
        try:
            with zipfile.ZipFile(compressed_file) as bundle:
                entries = self._filter_entries(bundle.namelist(), extract_dirs)

                for entry in entries:
                    print '{} {}'.format(extract_to, entry)
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
            self.exception('{}'.format(e.message))


    def deflate(self, file_object, mode, extract_to='.', extract_dirs='*', verbose=False):
        """This method allows to extract a tar, tar.bz2 and tar.gz file without writing to disk first.

        Args:
            file_object (object): Any file like object that is seekable.
            extract_to (str, optional): where to extract the compressed file.
        """
        compressed_file = StringIO(file_object.read())
        t = tarfile.open(fileobj=compressed_file, mode=mode)
        t.extractall(path=extract_to)


    def maybe_gzip(self, file_object, **kwargs):
        # XXX: Hack
        response = file_object
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


    def download_unpack(self, url, extract_to='.', extract_dirs='*', verbose=False):
        """Generic method to download and extract a compressed file without writing it to disk first.

        Args:
            url (str): URL where the file to be downloaded is located.
            extract_to (str): directory where the downloaded file will
                              be extracted to.
            extract_dirs (list, optional): directories inside the archive to extract.
                                           Defaults to `None`. It currently only applies to zip files.

        Raises:
            IOError: on `filename` file not found.

        """
        extract_dirs = '*' if extract_dirs is None else extract_dirs
        EXTENSION_TO_MIMETYPE = {
            'bz2': 'application/x-bzip2',
            'gz':  'application/x-gzip',
            'tar': 'application/x-tar',
            'zip': 'application/zip',
        }
        MIMETYPES = {
            'application/x-bzip2': {
                'function': self.deflate,
                'kwargs': {'mode': 'r:bz2'},
            },
            'application/x-gzip': {
                'function': self.deflate,
                'kwargs': {'mode': 'r:gz'},
            },
            'application/x-tar': {
                'function': self.deflate,
                'kwargs': {'mode': 'r'},
            },
            'application/zip': {
                'function': self.unzip,
            },
            'text/plain': {
                'function': self.maybe_gzip,
            },
        }

        parsed_url = urlparse.urlparse(url)

        # In case we're referrencing a file without file://
        if parsed_url.scheme == '':
            if not os.path.isfile(url):
                raise IOError('Could not find file to extract: {}'.format(url))

            url = 'file://%s' % os.path.abspath(url)
            parsed_fd = urlparse.urlparse(url)

        request = urllib2.Request(url)
        request.add_header('Accept-encoding', 'gzip')
        response = urllib2.urlopen(request)

        if parsed_url.scheme == 'file':
            filename = url.split('/')[-1]
            # XXX: bz2/gz instead of tar.{bz2/gz}
            extension = filename[filename.rfind('.')+1:]
            mimetype = EXTENSION_TO_MIMETYPE[extension]
        else:
            mimetype = response.headers.type

        self.debug('Url:\t\t\t{}'.format(url))
        self.debug('Mimetype:\t\t{}'.format(mimetype))
        self.debug('Content-Encoding\t{}'.format(response.headers.get('Content-Encoding')))

        function = MIMETYPES[mimetype]['function']
        kwargs = {
            'file_object': response,
            'extract_to': extract_to,
            'extract_dirs': extract_dirs,
            'verbose': verbose,
        }
        kwargs.update(MIMETYPES[mimetype].get('kwargs', {}))

        self.info('Downloading and extracting to {} these dirs {} from {}'.format(
            extract_to,
            ', '.join(extract_dirs),
            url,
        ))
        function(**kwargs)


def download_unpack_time(url, times, **kwargs):
    factory = DownloadUnpack()
    timings = []
    for i in range(0, times):
        start = time.time()
        factory.download_unpack(url, **kwargs)
        timings.append(time.time() - start)

    LOG.info(
        "Average {}  {}".format(
            round(reduce(lambda x, y: x + y, timings) / float(len(timings)), 4),
            url
        )
    )


if __name__ == "__main__":
    main()
