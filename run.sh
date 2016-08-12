#!/bin/sh
set -e
./create_archives.sh
echo "Here are the averages with the new unpacking methods with remote files:"
# None of these return the content-encoding
python download.py --url http://people.mozilla.org/~armenzg/archive.tar
python download.py --url http://people.mozilla.org/~armenzg/archive.tar.bz2
python download.py --url http://people.mozilla.org/~armenzg/archive.tar.gz
python download.py --url http://people.mozilla.org/~armenzg/archive.zip
echo ""

echo "Plain text; no gzip"
python download.py --url https://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470873261/firefox-51.0a1.en-US.linux-x86_64.txt
echo "Plain text; gzip"
python download.py --url http://people.mozilla.org/~armenzg/permanent/all_builders.txt
echo ""

echo "Here are the averages with the new unpacking methods with local files:"
python download.py --times 100 --url file://`pwd`/archive.tar
python download.py --times 100 --url file://`pwd`/archive.tar.bz2
python download.py --times 100 --url file://`pwd`/archive.tar.gz
python download.py --times 100 --url file://`pwd`/archive.zip
echo ""

echo "Here are the averages with the new unpacking methods with production files:"
python download.py --url http://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470319163/firefox-51.0a1.en-US.linux-x86_64.common.tests.zip
python download.py --url http://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470319163/firefox-51.0a1.en-US.linux-x86_64.tar.bz2
# XXX: Until we fix where we extract these files to
rm -rf bin/ certs/ config/ exte* firefox* jetpack/ jit-test/ jsreftest/ luciddream/ mach marionette/ modules/ mozbase/ mozinfo.json puppeteer/ steeplechase/ tools/ tps/
