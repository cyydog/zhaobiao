#!/bin/bash
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
export QDRANT_HOST=":memory:"

cd /Users/cxy/Projects/zhaobiao-dev/zhaobiao
.venv/bin/python indexer.py