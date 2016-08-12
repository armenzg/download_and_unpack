#!/bin/bash
# Script to auto-generate the different archive types under the archives directory.
# Based on whimboo's code

filename=log.txt
if [ ! -e "$filename" ]; then
  wget -q -N https://queue.taskcluster.net/v1/task/Q3DrENo_Rn61YJvTZlkIwQ/runs/0/artifacts/public%2Flogs%2Flive_backing.log
  gunzip live_backing.log -c > $filename
  rm live_backing.log
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

if [ ! -e archive.zip ]; then
  zip archive.zip "$filename"
fi
