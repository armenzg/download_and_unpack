#!/bin/sh
set -ex
./create_archives.sh
python download_normal.py --url http://localhost:8000/archive.tar.gz
python download_to_memory.py --url http://localhost:8000/archive.tar.gz
python download_stream.py --url http://localhost:8000/archive.tar.gz
