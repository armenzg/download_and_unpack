#! /usr/bin/env python
import fnmatch
import functools
import gzip
import httplib
import itertools
import logging
import os
import socket
import sys
import tarfile
import time
import urllib2
import urlparse
import zipfile
import zlib

from argparse import ArgumentParser
from cStringIO import StringIO

# mozharness log levels.
DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE = (
    'debug', 'info', 'warning', 'error', 'critical', 'fatal', 'ignore')


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


class Mozharness():
    config = {}

    def __init__(self):
        self.LOG = logging.getLogger()
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def info(self, msg):
        self.LOG.info(msg)

    def debug(self, msg):
        self.LOG.debug(msg)

    def warning(self, msg):
        self.LOG.warning(msg)

    def exception(self, msg):
        self.LOG.exception(msg)

    def log(self, message, level=INFO, exit_code=-1):
        # Simplifying the code
        self.LOG.info(message)

    # More complex commands {{{2
    def retry(self, action, attempts=None, sleeptime=60, max_sleeptime=5 * 60,
              retry_exceptions=(Exception, ), good_statuses=None, cleanup=None,
              error_level=ERROR, error_message="%(action)s failed after %(attempts)d tries!",
              failure_status=-1, log_level=INFO, args=(), kwargs={}):
        """ generic retry command. Ported from `util.retry`_

        Args:
            action (func): callable object to retry.
            attempts (int, optinal): maximum number of times to call actions.
                Defaults to `self.config.get('global_retries', 5)`
            sleeptime (int, optional): number of seconds to wait between
                attempts. Defaults to 60 and doubles each retry attempt, to
                a maximum of `max_sleeptime'
            max_sleeptime (int, optional): maximum value of sleeptime. Defaults
                to 5 minutes
            retry_exceptions (tuple, optional): Exceptions that should be caught.
                If exceptions other than those listed in `retry_exceptions' are
                raised from `action', they will be raised immediately. Defaults
                to (Exception)
            good_statuses (object, optional): return values which, if specified,
                will result in retrying if the return value isn't listed.
                Defaults to `None`.
            cleanup (func, optional): If `cleanup' is provided and callable
                it will be called immediately after an Exception is caught.
                No arguments will be passed to it. If your cleanup function
                requires arguments it is recommended that you wrap it in an
                argumentless function.
                Defaults to `None`.
            error_level (str, optional): log level name in case of error.
                Defaults to `ERROR`.
            error_message (str, optional): string format to use in case
                none of the attempts success. Defaults to
                '%(action)s failed after %(attempts)d tries!'
            failure_status (int, optional): flag to return in case the retries
                were not successfull. Defaults to -1.
            log_level (str, optional): log level name to use for normal activity.
                Defaults to `INFO`.
            args (tuple, optional): positional arguments to pass onto `action`.
            kwargs (dict, optional): key-value arguments to pass onto `action`.

        Returns:
            object: return value of `action`.
            int: failure status in case of failure retries.
        """
        if not callable(action):
            self.fatal("retry() called with an uncallable method %s!" % action)
        if cleanup and not callable(cleanup):
            self.fatal("retry() called with an uncallable cleanup method %s!" % cleanup)
        if not attempts:
            attempts = self.config.get("global_retries", 5)
        if max_sleeptime < sleeptime:
            self.debug("max_sleeptime %d less than sleeptime %d" % (
                       max_sleeptime, sleeptime))
        n = 0
        while n <= attempts:
            retry = False
            n += 1
            try:
                self.log("retry: Calling %s with args: %s, kwargs: %s, attempt #%d" %
                         (action.__name__, str(args), str(kwargs), n), level=log_level)
                status = action(*args, **kwargs)
                if good_statuses and status not in good_statuses:
                    retry = True
            except retry_exceptions, e:
                retry = True
                error_message = "%s\nCaught exception: %s" % (error_message, str(e))
                self.log('retry: attempt #%d caught exception: %s' % (n, str(e)), level=INFO)

            if not retry:
                return status
            else:
                if cleanup:
                    cleanup()
                if n == attempts:
                    self.log(error_message % {'action': action, 'attempts': n}, level=error_level)
                    return failure_status
                if sleeptime > 0:
                    self.log("retry: Failed, sleeping %d seconds before retrying" %
                             sleeptime, level=log_level)
                    time.sleep(sleeptime)
                    sleeptime = sleeptime * 2
                    if sleeptime > max_sleeptime:
                        sleeptime = max_sleeptime


# I'm making this module a class to make it easier to compare with Mozharness' code
class DownloadUnpack(Mozharness):
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
