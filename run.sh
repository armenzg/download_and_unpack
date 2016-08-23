#!/bin/sh
set -e
./create_archives.sh
script="`pwd`/download.py"
pwd="`pwd`"
mkdir -p temp
cd temp
echo "Here are the averages with the new unpacking methods with remote files:"
# None of these return the content-encoding
python $script --url http://people.mozilla.org/~armenzg/archive.tar
python $script --url http://people.mozilla.org/~armenzg/archive.tar.bz2
python $script --url http://people.mozilla.org/~armenzg/archive.tar.gz
python $script --url http://people.mozilla.org/~armenzg/archive.zip
echo ""

echo "Plain text; no gzip"
python $script --url https://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470873261/firefox-51.0a1.en-US.linux-x86_64.txt
echo "Plain text; gzip"
python $script --url http://people.mozilla.org/~armenzg/permanent/all_builders.txt
echo ""

echo "Here are the averages with the new unpacking methods with local files:"
python $script --times 100 --url file://$pwd/archive.tar
python $script --times 100 --url file://$pwd/archive.tar.bz2
python $script --times 100 --url file://$pwd/archive.tar.gz
python $script --times 100 --url file://$pwd/archive.zip
python $script --extract-dirs dir1/* --url file://$pwd/archive.zip
echo ""

echo "Here are the averages with the new unpacking methods with production files:"
python $script --url http://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470319163/firefox-51.0a1.en-US.linux-x86_64.common.tests.zip --extract-to tests
python $script --url http://archive.mozilla.org/pub/firefox/tinderbox-builds/mozilla-central-linux64/1470319163/firefox-51.0a1.en-US.linux-x86_64.tar.bz2 --extract-to firefox
