#!/bin/bash
# Script to auto-generate the different archive types under the archives directory.
# Based on whimboo's code

# filename=Firefox\ 47.0.1.dmg
# if [ ! -e "$filename" ]; then
#   wget -q -N https://download-installer.cdn.mozilla.net/pub/firefox/releases/47.0.1/mac/en-US/Firefox%2047.0.1.dmg
# fi

# Using a log is a much smaller file to download
filename=live_backing.log
if [ ! -e "$filename" ]; then
  wget -q -N https://public-artifacts.taskcluster.net/X_Z6IquRSoKiQMPctHK0PA/0/public/logs/live_backing.log
fi


if [ ! -e archive.tar ]; then
  tar -cf archive.tar "$filename"
fi

if [ ! -e archive.tar.gz ]; then
  gzip -fk archive.tar >archive.tar.gz
fi

if [ ! -e archive.tar.bz2 ]; then
  bzip2 -fk archive.tar >archive.tar.bz2
fi
