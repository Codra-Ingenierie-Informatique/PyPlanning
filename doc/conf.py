# -*- coding: utf-8 -*-

# pylint: skip-file

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

import planning  # noqa: E402

# -- Project information -----------------------------------------------------

project = "PyPlanning"
author = ""
copyright = "2024, PyPlanning Developers"
html_logo = latex_logo = "_static/PyPlanning-title.png"
release = planning.__version__

# -- General configuration ---------------------------------------------------

extensions = []
templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_theme_options = {"show_toc_level": 2}
htmlhelp_basename = project
html_static_path = ["_static"]
