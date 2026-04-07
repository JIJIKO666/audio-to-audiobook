#!/usr/bin/env python3
"""
Audiobook Maker — legacy entry point shim.
Kept so existing launch scripts and .spec files don't break.
"""
from main import main

if __name__ == "__main__":
    main()
