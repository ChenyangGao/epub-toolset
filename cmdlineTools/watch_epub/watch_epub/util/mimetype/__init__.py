#!/usr/bin/env python
# coding: utf-8

__all__ = ["guess_mimetype"]

# Reference:
# https://docs.python.org/3/library/mimetypes.html
# https://www.iana.org/assignments/media-types/media-types.xhtml
# https://www.w3.org/publishing/epub3/epub-spec.html#sec-cmt-supported
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
# https://mimetype.io/all-types/
# https://pypi.org/project/filetype/
# https://pypi.org/project/python-magic/

from . import _001_http_common_mime_types
from . import _002_mime_file_extension
from . import _003_mime_all_types

import mimetypes

if not mimetypes.inited:
    mimetypes.init()

from mimetypes import guess_type
from os import fsdecode, PathLike
from typing import Optional, Union


def guess_mimetype(path: Union[bytes, str, PathLike]) -> Optional[str]:
    return guess_type(fsdecode(path))[0]

