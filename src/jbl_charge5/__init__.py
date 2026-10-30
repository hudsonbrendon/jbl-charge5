"""Reverse-engineered JBL Charge 5 control protocol."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("jbl-charge5")
except PackageNotFoundError:  # checkout without `pip install -e .`
    __version__ = "0.0.0"
