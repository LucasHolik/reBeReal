"""Metadata writers — inject EXIF, XMP, and IPTC into output images."""

from rebereal.metadata.base import MetadataWriter
from rebereal.metadata.composite import CompositeMetadataWriter
from rebereal.metadata.exif_writer import ExifWriter
from rebereal.metadata.iptc_writer import IptcWriter
from rebereal.metadata.xmp_writer import XmpWriter

__all__ = [
    "MetadataWriter",
    "CompositeMetadataWriter",
    "ExifWriter",
    "XmpWriter",
    "IptcWriter",
]
