# -*- coding: utf-8 -*-
"""Testing PyPlanning data model"""

import os
import os.path as osp
import time
import webbrowser
import xml.etree.ElementTree as ET

from planning.config import TESTPATH
from planning.model import PlanningData


def test_chart():
    """Test data model features by generating a chart"""

    fname = osp.join(TESTPATH, "test.xml")
    planning = PlanningData.from_filename(fname)
    planning.generate_charts()
    for index, url in enumerate(planning.chart_filenames):
        cmd = webbrowser.open if index == 0 else webbrowser.open_new_tab
        cmd(url)
        time.sleep(0.3)
    os.startfile(TESTPATH)


def get_file_contents(fname):
    """Get file contents"""
    with open(fname, "rb") as fdesc:
        contents = fdesc.read().decode("utf-8")
    return contents


def parse_and_write_xml(fname1, fname2):
    """Parse XML file and write it to another file"""
    tree1 = ET.ElementTree()
    tree1.parse(fname1)
    tree2 = ET.ElementTree(tree1.getroot())
    ET.indent(tree2)
    tree2.write(fname2, encoding="utf-8")


def test_io():
    """Test data model serialize/deserialize features"""
    fname = osp.join(TESTPATH, "test.xml")
    fname1 = fname.replace(".xml", "-in.xml")
    fname2 = fname.replace(".xml", "-out.xml")
    parse_and_write_xml(fname, fname1)
    planning = PlanningData.from_filename(fname1)
    planning.to_filename(fname2)
    cont1 = get_file_contents(fname1)
    cont2 = get_file_contents(fname2)
    assert cont1 == cont2


if __name__ == "__main__":
    test_io()
    test_chart()
