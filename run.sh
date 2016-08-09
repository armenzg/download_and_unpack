#!/bin/sh
set -ex
./create_archives.sh
echo "Here are the averages with the new unpacking methods with local files:"
python download.py --times 100
echo "Here are the averages with the new unpacking methods with real files:"
python download.py --url http://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470319163/firefox-51.0a1.en-US.linux-x86_64.common.tests.zip
python download.py --url http://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470319163/firefox-51.0a1.en-US.linux-x86_64.tar.bz2
