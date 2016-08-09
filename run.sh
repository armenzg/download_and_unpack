#!/bin/sh
set -ex
./create_archives.sh
echo "Here are the averages with the new unpacking methods with local files:"
python download.py --times 100
echo "Here are the averages with the new unpacking methods with production files:"
python download.py --url http://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470319163/firefox-51.0a1.en-US.linux-x86_64.common.tests.zip
python download.py --url http://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470319163/firefox-51.0a1.en-US.linux-x86_64.tar.bz2
# XXX: Until we fix where we extract these files to
rm -rf bin/ certs/ config/ exte* firefox* jetpack/ jit-test/ jsreftest/ luciddream/ mach marionette/ modules/ mozbase/ mozinfo.json puppeteer/ steeplechase/ tools/ tps/
