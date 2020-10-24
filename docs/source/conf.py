# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

import os
import sys

import sphinx_rtd_theme

sys.path.insert(0, os.path.abspath("./../.."))


# -- Project information -----------------------------------------------------

project = "NautilusTrader"
copyright = "2015-2020, Nautech Systems Pty Ltd."
author = "Nautech Systems"

version = ""

if "READTHEDOCS" not in os.environ:
    # if developing locally, use pyro.__version__ as version
    from nautilus_trader import __version__  # noqaE402
    version = __version__

# release version
release = version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    'sphinx.ext.doctest',
    "sphinx.ext.coverage",
    "sphinx.ext.intersphinx",
    'sphinx.ext.viewcode',
    "numpydoc",
]

# The master toctree document.
master_doc = "index"

# do not prepend module name to functions
add_module_names = False
todo_include_todos = False

autosummary_generate = True
numpydoc_show_class_members = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
html_copy_source = False
html_show_sourcelink = False

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_style = "css/nautilus.css"
html_logo = "_static/img/nautilus-black.png"
