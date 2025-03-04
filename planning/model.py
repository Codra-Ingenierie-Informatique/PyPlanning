"""PyPlanning data model"""

# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

import datetime
import locale
import os.path as osp
import re
import uuid
import xml.etree.ElementTree as ET
from copy import deepcopy
from enum import Enum
from io import StringIO
from typing import Any, Generator, Generic, Optional, TypeVar, Union

from planning import __version__, gantt
from planning.config import MAIN_FONT_FAMILY, _

locale.setlocale(locale.LC_TIME, "")

VERSION = ".".join(__version__.split(".", 2)[0:2])

gantt.define_font_attributes(
    fill="black", stroke="black", stroke_width=0, font_family=MAIN_FONT_FAMILY
)

_T = TypeVar("_T")
AbstractDataT = TypeVar("AbstractDataT", bound="AbstractData")
ResourceDataT = TypeVar("ResourceDataT", bound="ResourceData")
ChartDataT = TypeVar("ChartDataT", bound="ChartData")
TaskDataT = TypeVar("TaskDataT", bound="TaskData")
MilestoneDataT = TypeVar("MilestoneDataT", bound="MilestoneData")
LeaveDataT = TypeVar("LeaveDataT", bound="LeaveData")
AnyData = Union[
    "AbstractData",
    "ResourceData",
    "ChartData",
    "TaskData",
    "MilestoneData",
    "LeaveData",
    "AbstractTaskData",
    "ProjectData",
]


class DTypes(Enum):
    """This is the enum for supported data types"""

    TEXT = 0
    DAYS = 1
    DATE = 2
    COLOR = 3
    INTEGER = 4
    LIST = 5
    CHOICE = 6
    MULTIPLE_CHOICE = 7
    BOOLEAN = "🗸"
    LONG_TEXT = 9
    FLOAT = 10


class DefaultChoiceMode(Enum):
    NONE = 0
    FIRST = 1
    ALL = 2


class NoDefault:
    """No default value"""


class DataItem(Generic[_T]):
    """Data elementary item"""

    COLORS: dict[str, str | None] = {
        "": None,
        "orange": "#fab978",
        "red": "#e47172",
        "blue": "#53ccff",
        "brown": "#591b1b",
        "yellow": "#ffd966",
        "cyan": "#c6eeff",
        "silver": "#9c9ea0",
        "green": "#b0d184",
        "magenta": "#aa5ae6",
        "_merge_warn": "#ff0000",
    }

    def __init__(
        self,
        parent: AbstractDataT,
        name: str,
        datatype: DTypes,
        value: Optional[_T],
        choices: Optional[dict[Any, Any]] = None,
        default_choice_mode=DefaultChoiceMode.FIRST,
    ):
        self.parent: AbstractDataT = parent
        self.name = name
        self.datatype = datatype
        self.__value = value
        self.choices: dict[Any, _T] = choices or {}  # tuple of (key, value) tuples
        if datatype in (DTypes.CHOICE, DTypes.MULTIPLE_CHOICE) and choices is None:
            raise ValueError("Choices must be specified")
        self.default_choice_mode = default_choice_mode

    @property
    def value(self) -> Optional[_T]:
        """Return value"""
        return self.__value

    @value.setter
    def value(self, value: Optional[_T]):
        """Set value"""
        self.__value = value

    @property
    def choice_keys(self):
        """Return choice keys"""
        if self.choices is not None:
            return list(self.choices.keys())
        return []

    @property
    def choice_values(self):
        """Return choice values"""
        if self.choices is not None:
            return list(self.choices.values())
        return []

    def get_choice_value(self) -> _T | None:
        """Return choice value"""
        if len(self.choices.keys()) == 0:
            return None
        if self.value is None:
            return list(self.choices.values())[0]
        if self.value in self.choices.keys():
            return self.choices[self.value]
        raise ValueError(f"No key {self.value} in choices")

    def get_choices_values(self) -> list[_T]:
        """Return choices value"""
        if len(self.choices) == 0:
            return []
        if self.value is None:
            return [list(self.choices.values())[0]]
        choices = [self.choices[key] for key in self.value]
        if not choices and self.value:
            raise ValueError(f"No key {self.value} in choices")
        return choices

    def set_choice_value(self, value):
        """Set item value by choice value"""
        if len(self.choices) == 0:
            return
        for key, val in self.choices.items():
            if val == value:
                self.value = key
                break
        else:
            raise ValueError(f"No value {value} in choices")

    def get_html_color(self, strval):
        """Return HTML color string"""
        if strval in self.COLORS:
            return self.COLORS[strval]
        if strval.startswith("#"):
            return strval
        for fullname, color in self.COLORS.items():
            if fullname.startswith(strval):
                return color
        raise ValueError(f"Unknown color name '{strval}'")

    @classmethod
    def from_element(
        cls,
        parent,
        element,
        name,
        datatype,
        default: Optional[_T | type[NoDefault]] = NoDefault,
        choices=None,
    ):
        """Setup item from XML element"""
        if default is NoDefault:
            default = None
        strval = element.get(name)
        if strval is None:
            return cls(parent, name, datatype, default, choices)
        instance = cls(parent, name, datatype, None, choices)
        instance.from_text(strval)
        return instance

    def to_widget_value(self):
        """Convert model value to widget set value"""
        if self.value is None:
            if self.datatype == DTypes.DAYS:
                return 1
            if self.datatype == DTypes.DATE:
                return datetime.date.today()
            if self.datatype == DTypes.CHOICE:
                if len(self.choices.keys()) == 0:
                    return ""
                return self.choice_keys[0]
            if self.datatype == DTypes.TEXT or self.datatype == DTypes.LONG_TEXT:
                return ""
            if self.datatype == DTypes.BOOLEAN:
                return False
            if self.datatype == DTypes.INTEGER:
                return ""
            if self.datatype == DTypes.COLOR:
                if self.value is None:
                    return None
                for cname in self.COLORS:
                    if cname == self.value or cname.startswith(
                        self.value
                    ):  # retrocompatibility
                        return cname
            if self.datatype == DTypes.LIST:
                return ""
            if self.datatype == DTypes.MULTIPLE_CHOICE:
                return []
            raise NotImplementedError

        if self.datatype == DTypes.INTEGER:
            return str(self.value)
        if self.datatype == DTypes.LIST:
            return ", ".join(self.value)
        return self.value

    def to_display(self):
        """Convert widget value or data model value to display value"""
        if self.datatype == DTypes.DAYS and self.value is not None:
            text = str(self.value) + " " + _("day")
            if self.value > 1:
                text += "s"
            return text
        if self.datatype in (DTypes.CHOICE, DTypes.MULTIPLE_CHOICE):
            if self.value is None:
                if (
                    self.default_choice_mode is DefaultChoiceMode.NONE
                    or len(self.choices.keys()) == 0
                ):
                    return None
                elif self.default_choice_mode is DefaultChoiceMode.FIRST:
                    return self.choice_values[0]
            elif self.datatype is DTypes.CHOICE:
                return self.get_choice_value()
            elif self.datatype is DTypes.MULTIPLE_CHOICE:
                return ", ".join(str(v) for v in self.get_choices_values())
        if self.datatype == DTypes.BOOLEAN:
            if self.value:
                return DTypes.BOOLEAN.value
            return ""
        return self.to_text()

    def from_display(self, widget_value):
        """Convert back from display value"""
        if self.datatype == DTypes.CHOICE:
            if widget_value not in self.choice_values:
                raise ValueError(f"No value {widget_value} in choices")
            self.set_choice_value(widget_value)
        elif self.datatype == DTypes.MULTIPLE_CHOICE:
            self.value = []
            split_values = []
            for val in widget_value.split(","):
                strip_val = val.strip()
                if strip_val:
                    split_values.append(strip_val)
            for key, ref_val in self.choices.items():
                for val in split_values:
                    if ref_val == val:
                        self.value.append(key)

        elif self.datatype == DTypes.BOOLEAN:
            self.value = widget_value == DTypes.BOOLEAN.value
        else:
            self.from_text(widget_value)

    def to_text(self) -> str:
        """Convert widget value or data model value to text representation"""
        val = self.value
        if val is None:
            return ""
        if self.datatype == DTypes.TEXT or self.datatype == DTypes.LONG_TEXT:
            return str(val)
        if self.datatype in (DTypes.INTEGER, DTypes.DAYS):
            return str(val)
        if self.datatype == DTypes.LIST:
            return ", ".join(val)
        if self.datatype == DTypes.CHOICE:
            if val not in self.choice_keys:
                raise ValueError(f"No key {val} in choices")
            return val
        if self.datatype == DTypes.COLOR:
            for cname, cvalue in self.COLORS.items():
                if cvalue == val:
                    return cname
            return val
        if self.datatype == DTypes.DATE:
            return val.strftime("%d/%m/%y")
        if self.datatype == DTypes.BOOLEAN:
            return str(val)
        if self.datatype == DTypes.MULTIPLE_CHOICE:
            if self.value is None:
                return ""
            return ", ".join(self.value)
        raise NotImplementedError(f"Unsupported datatype {self.datatype}")

    def from_text(self, text: str):
        """Set data item value from text"""
        if self.datatype == DTypes.COLOR:
            self.value = self.get_html_color(text)
        elif self.datatype == DTypes.TEXT or self.datatype == DTypes.LONG_TEXT:
            self.value = None if len(text) == 0 else text.strip()
        elif self.datatype == DTypes.INTEGER:
            self.value = None if text == "" else int(text)
        elif self.datatype == DTypes.FLOAT:
            self.value = None if text == "" else float(text)
        elif self.datatype == DTypes.LIST:
            if text == "":
                self.value = []
            else:
                values = text.split(",")
                values_f = [v for val in values if (v := val.strip())]
                self.value = values_f

        elif self.datatype == DTypes.CHOICE:
            if text not in self.choice_keys:
                raise ValueError(f"No key {text} in choices")
            self.value = text
        elif self.datatype == DTypes.DAYS:
            if text == "":  # No value in data model
                self.value = 1
            else:
                self.value = int(text.split(" ")[0])
        elif self.datatype == DTypes.DATE:
            if text == "":  # No value in data model
                self.value = datetime.date.today()
            else:
                self.value = datetime.datetime.strptime(text, "%d/%m/%y").date()
        elif self.datatype == DTypes.BOOLEAN:
            self.value = text.lower() in ("", "true")
        elif self.datatype == DTypes.MULTIPLE_CHOICE:
            self.value = []
            for val in text.split(","):
                strip_val = val.strip()
                if strip_val:
                    self.value.append(strip_val)
        else:
            raise NotImplementedError(f"Unsupported datatype {self.datatype}")


class AbstractData:
    """Abstract data set (associated with an XML element)"""

    TAG = None
    DEFAULT_ICON_NAME = None
    DEFAULT_NAME = None
    DEFAULT_COLOR = None
    READ_ONLY_ITEMS = ()
    __NO_COPY: tuple[str, ...] = ("pdata",)
    DEFAULT_ID_PREFIX = "default"

    def __init__(self, pdata: "PlanningData", name=None, fullname=None):
        self.pdata = pdata
        self.element = None
        if name is None:
            name = self.DEFAULT_NAME
        color = self.DEFAULT_COLOR
        self.name = DataItem[str](self, "name", DTypes.TEXT, name)
        self.fullname = DataItem[str](self, "fullname", DTypes.TEXT, fullname)
        self.color = DataItem[str](self, "color", DTypes.COLOR, color)
        self.project = DataItem[str](self, "project", DTypes.CHOICE, None, {})

        self._default_id = ""
        self.id = DataItem[str](self, "id", DTypes.TEXT, self.default_id)
        self.__gantt_object = None

    def create_id(self, custom_prefix=None, forbidden_ids=None) -> str:
        if forbidden_ids is None:
            forbidden_ids = []
        prefix = custom_prefix or self.DEFAULT_ID_PREFIX
        new_id = f"{prefix}-{uuid.uuid4().hex[:6]}"
        while self.pdata.get_data_from_id(new_id) or new_id in forbidden_ids:
            new_id = f"{prefix}-{uuid.uuid4().hex[:6]}"
        return new_id

    @property
    def default_id(self) -> str:
        if self._default_id == "" and self.pdata is not None:
            self._default_id = self.create_id()
        return self._default_id

    def duplicate(self):
        """Duplicate data set"""
        cls = self.__class__
        new_data = cls.__new__(cls)
        for name, value in self.__dict__.items():
            if name in self.__NO_COPY and value:
                setattr(new_data, name, value)
                continue
            copied_value = deepcopy(value)
            if isinstance(copied_value, DataItem):
                copied_value.parent = new_data
            setattr(new_data, name, copied_value)

        copy_pattern = re.compile(r"\((\d+)\)$")
        if re.search(copy_pattern, str(new_data.name.value)):
            new_data.name.value = re.sub(
                copy_pattern,
                lambda m: f"({int(m.group(1)) + 1})",
                str(new_data.name.value),
            )
        else:
            new_data.name.value = f"{new_data.name.value} (1)"

        new_data.id.value = new_data.create_id()
        return new_data

    @property
    def gantt_object(
        self,
    ) -> gantt.Resource | gantt.Task | gantt.Milestone | gantt.Project | None:
        """Return associated gantt object"""
        return self.__gantt_object

    @gantt_object.setter
    def gantt_object(self, value):
        """Set associated gantt object value"""
        self.__gantt_object = value

    @property
    def has_named_id(self):
        """Return True if data set has a named ID (as opposed to an internal
        ID which is automatically generated and not suited for display"""
        return self.id.value != self.default_id

    @property
    def has_project(self):
        """Return True if data project item is valid"""
        return self.project is not None and bool(self.project.value)

    def is_read_only(self, name: str):
        """Return True if item name is read-only"""
        return name in self.READ_ONLY_ITEMS

    def _init_from_element(self, element: ET.Element):
        """Init instance from XML element"""
        self.element = element
        self.name: DataItem[str] = self.get_str("name", default=self.DEFAULT_NAME)
        self.fullname: DataItem[str] = self.get_str("fullname")
        self.color: DataItem[str] = self.get_color(default=self.DEFAULT_COLOR)

        self._check_create_missing_project(element)

        self.project: DataItem[str] = self.get_choices(
            "project", default=None, choices=self.pdata.project_choices()
        )

        self.id: DataItem[str] = self.get_str("id", default=self.default_id)

    @classmethod
    def from_element(cls, pdata, element):
        """Instantiate data set from XML element"""
        instance = cls(pdata)
        instance._init_from_element(element)
        return instance

    def to_element(self, parent=None):
        """Serialize data set to element"""
        return ET.SubElement(parent, self.TAG, attrib=self.get_attrib_dict())

    def get_attrib_dict(self):
        """Return attribute dictionary for XML serialization"""
        attrib = {}
        for name in self.get_attrib_names():
            ditem = getattr(self, name, None)
            if (
                ditem is not None
                and ditem.value not in (None, [])
                and not self.is_read_only(ditem.name)
            ):
                attrib[name] = ditem.to_text()
        return attrib

    def _check_create_missing_project(self, element: ET.Element):
        """Check if project attribute is set and is an exisiting project id. If not,
        checks if it is an existing project name. If not, creates a new project.

        Args:
            element: element which can contain a project attribute to check
        """
        project_attr = element.get("project", None)
        if project_attr is not None and project_attr not in self.pdata.projects:
            project_names = tuple(prj.name.value for prj in self.pdata.prjlist)
            if project_attr not in project_names:
                new_project = ProjectData(self.pdata, name=project_attr)
                self.pdata.add_project(new_project, None)
                element.set("project", new_project.id.value or "")
            else:
                project_index = project_names.index(project_attr)
                project = self.pdata.prjlist[project_index]
                element.set("project", project.id.value or "")

    def get_attrib_names(self):
        """Return attribute names"""
        attrib = ["name", "fullname", "project", "color"]
        if self.has_named_id:
            attrib += ["id"]
        return attrib

    def has_item(self, item_name):
        """Return True if item is set"""
        item = getattr(self, item_name)
        has_item = item is not None and item.value is not None
        return has_item

    def is_not_set_but_required(self, check_name, item_name):
        """Return True if item is not set but required"""
        return check_name == item_name and not self.has_item(item_name)

    def is_set_but_not_expected(self, check_name, item_name):
        """Return True if item is set but not expected"""
        return check_name == item_name and self.has_item(item_name)

    def is_valid(self, item_name):  # pylint: disable=W0613
        """Check data item values, eventually depending on planning data"""
        return True

    def get_icon_name(self, item_name):
        """Return icon name associated with data set"""
        if not self.is_valid(item_name):
            return "invalid.svg"
        if item_name in ("name", "fullname"):
            return self.DEFAULT_ICON_NAME
        return None

    def create_item(
        self,
        name: str,
        datatype: DTypes,
        default: Optional[_T | type[NoDefault]] = None,
        choices: Optional[list] = None,
    ):
        """Create new data item"""
        return DataItem.from_element(
            self, self.element, name, datatype, default, choices
        )

    def get_str(self, name: str, default: Optional[_T | type[NoDefault]] = NoDefault):
        """Get value from XML element and set its datatype"""
        return self.create_item(name, DTypes.TEXT, default=default)

    def get_long_text(
        self, name: str, default: Optional[_T | type[NoDefault]] = NoDefault
    ):
        """Get value from XML element and set its datatype"""
        return self.create_item(name, DTypes.LONG_TEXT, default=default)

    def get_color(self, default: Optional[_T | type[NoDefault]] = NoDefault):
        """Get color value (html code) from XML attribute"""
        return self.create_item("color", DTypes.COLOR, default=default)

    def get_date(self, name, default: Optional[_T | type[NoDefault]] = NoDefault):
        """Get datetime value from XML attribute"""
        return self.create_item(name, DTypes.DATE, default=default)

    def get_days(self, name, default: Optional[_T | type[NoDefault]] = NoDefault):
        """Get days number value from XML attribute"""
        return self.create_item(name, DTypes.DAYS, default=default)

    def get_int(self, name, default: Optional[_T | type[NoDefault]] = NoDefault):
        """Get integer value from XML attribute"""
        return self.create_item(name, DTypes.INTEGER, default=default)

    def get_float(self, name, default: Optional[_T | type[NoDefault]] = NoDefault):
        """Get float value from XML attribute"""
        return self.create_item(name, DTypes.FLOAT, default=default)

    def get_list(self, name, default: Optional[_T | type[NoDefault]] = NoDefault):
        """Get list value from XML attribute"""
        return self.create_item(name, DTypes.LIST, default=default)

    def get_choices(
        self,
        name,
        default: Optional[_T | type[NoDefault]] = NoDefault,
        choices=None,
        default_mode=DefaultChoiceMode.FIRST,
    ):
        """Get choices value from XML attribute"""
        ditem = self.create_item(name, DTypes.CHOICE, default=default, choices=choices)
        ditem.default_choice_mode = default_mode
        return ditem

    def get_multi_choices(
        self,
        name,
        default: Optional[_T | type[NoDefault]] = NoDefault,
        choices=None,
        default_mode=DefaultChoiceMode.FIRST,
    ):
        """Get choices value from XML attribute"""
        ditem = self.create_item(
            name,
            DTypes.MULTIPLE_CHOICE,
            default=default,
            choices=choices,
        )
        ditem.default_choice_mode = default_mode
        return ditem

    def get_bool(self, name, default: Optional[_T | type[NoDefault]] = NoDefault):
        """Get boolean value from XML attribute"""
        return self.create_item(name, DTypes.BOOLEAN, default=default)

    def process_gantt(self):
        """Create or update Gantt objects and add them to dictionaries"""


class AbstractDurationData(AbstractData):
    """Duration data set"""

    def __init__(self, pdata, name=None, fullname=None):
        super().__init__(pdata, name, fullname)
        self.start = DataItem(self, "start", DTypes.DATE, None)
        self.stop = DataItem(self, "stop", DTypes.DATE, None)
        self.duration = DataItem(self, "duration", DTypes.DAYS, None)

    @property
    def has_start(self):
        """Return True if data start item is valid"""
        return self.start is not None and self.start.value is not None

    @property
    def has_stop(self):
        """Return True if data stop item is valid"""
        return self.stop is not None and self.stop.value is not None

    @property
    def has_duration(self):
        """Return True if data duration item is valid"""
        return self.duration is not None and self.duration.value is not None

    def _init_from_element(self, element):
        """Init instance from XML element"""
        super()._init_from_element(element)
        self.start = self.get_date("start")
        self.stop = self.get_date("stop")
        self.duration = self.get_days("duration")

    def get_attrib_names(self):
        """Return attribute names"""
        return ["start", "stop", "duration"] + super().get_attrib_names()

    def is_valid(self, item_name):
        """Check data item values, eventually depending on planning data"""
        if item_name in ("stop", "duration"):
            return not (self.has_stop and self.has_duration)
        return True


class ChartData(AbstractDurationData):
    """Chart data set"""

    GANTT_SCALES = {
        "d": gantt.DRAW_WITH_DAILY_SCALE,
        "w": gantt.DRAW_WITH_WEEKLY_SCALE,
        "m": gantt.DRAW_WITH_MONTHLY_SCALE,
        "q": gantt.DRAW_WITH_QUATERLY_SCALE,  # Not supported yet actually
    }
    SCALES = {
        "d": _("Days"),
        "w": _("Weeks"),
        "m": _("Months"),
    }
    TYPES = {"r": _("Resources - Line"), "rg": _("Resources - Gantt"), "g": _("Macro resources"), "t": _("Tasks"), "m": _("Macro tasks")}
    TAG = "CHART"
    DEFAULT_ICON_NAME = "chart.svg"
    READ_ONLY_ITEMS = ("fullname", "color")
    DEFAULT_ID_PREFIX = "chart"

    def __init__(self, pdata, name=None, fullname=None):
        super().__init__(pdata, name, fullname)
        self.scale = DataItem(self, "scale", DTypes.CHOICE, None, self.SCALES)
        self.type = DataItem(self, "type", DTypes.CHOICE, None, self.TYPES)
        self.today = DataItem(self, "today", DTypes.DATE, None)
        self.offset = DataItem(self, "offset", DTypes.INTEGER, None)
        self.t0mode = DataItem(self, "t0mode", DTypes.BOOLEAN, None)
        self.projects = DataItem[list[str]](
            self, "projects", DTypes.MULTIPLE_CHOICE, None, {}, DefaultChoiceMode.NONE
        )
        self.is_default_name = self.set_is_default_name()

    def set_is_default_name(self) -> bool:
        """Check if name is default and sets the "is_default_name" attribute

        Returns:
            bool: True if name is default, False otherwise
        """
        if self.pdata is None or self.pdata.filename is None:
            self.is_default_name = False
            return False
        xml_prefix, _ext = osp.basename(str(self.pdata.filename)).rsplit(".", 1)
        default_name_re = re.compile(
            rf"^{xml_prefix}(_?\d{{2}})?(\.svg)?$", re.IGNORECASE
        )
        is_default_name = self.name.value is None or bool(
            default_name_re.match(str(self.name.value))
        )
        self.is_default_name = is_default_name
        return is_default_name

    def _init_from_element(self, element):
        """Init instance from XML element"""
        super()._init_from_element(element)
        self.scale = self.get_choices("scale", choices=self.SCALES)
        self.type = self.get_choices("type", choices=self.TYPES)
        self.today = self.get_date("today")
        self.offset = self.get_int("offset")
        self.t0mode = self.get_bool("t0mode")
        self.projects = self.get_multi_choices(
            "projects", [], self.pdata.project_choices(), DefaultChoiceMode.NONE
        )
        if self.projects.value is not None and self.project.value is not None:
            self.projects.value = [self.project.value]
            self.project.value = None
        self.set_is_default_name()

    def get_attrib_names(self):
        """Return attribute names"""
        attrib_names = super().get_attrib_names()
        if self.is_default_name:
            attrib_names.remove("name")
        return attrib_names + ["today", "type", "scale", "offset", "t0mode", "projects"]

    def is_valid(self, item_name: str):
        """Check data item values, eventually depending on planning data"""
        if not super().is_valid(item_name):
            return False
        if self.is_not_set_but_required(item_name, "start"):
            return False
        if self.is_not_set_but_required(item_name, "stop"):
            return False
        if self.is_set_but_not_expected(item_name, "duration"):
            return False
        if item_name == "project" and self.has_project:
            return self.project.value in self.pdata.get_task_project_names()
        if item_name == "projects" and self.projects.value:
            pids = set(self.pdata.projects.keys())
            return all(pid in pids for pid in self.projects.value)
        if item_name in ("start", "stop"):
            if not self.has_start or not self.has_stop:
                return True
            return self.stop.value >= self.start.value
        return True

    def set_today(self):
        """Set today item value to... today"""
        self.today.value = datetime.date.today()

    def set_chart_filename(self, xml_filename: str, index: int):
        """Set chart index, and then chart name to default xml_filename+index if no
        name is set.

        Args:
            filename (str): The filename of the chart
            index (int): The index of the chart. Not used for now.
        """
        if xml_filename is None:
            return
        xml_prefix = osp.splitext(osp.basename(xml_filename))[0]
        if self.is_default_name or self.name.value is None:
            bname = xml_prefix + f"_{index:02d}.svg"
        else:
            bname = str(self.name.value)
            if not bname.endswith(".svg"):
                bname += ".svg"

        filepath = osp.join(osp.dirname(xml_filename), bname)

        self.name.value = bname
        self.fullname.value = filepath

    def make_svg(
        self,
        project: gantt.Project,
        one_line_for_tasks,
        show_title=False,
        show_conflicts=False,
        tu_width=1.0,
        tu_fraction=True,
    ):
        """Make chart SVG"""
        filename = self.fullname.value
        if filename is None:
            return
        offset = 5.5 if self.offset.value is None else self.offset.value
        ptype = "r" if self.type.value is None else self.type.value
        scale_key = "d" if self.scale.value is None else self.scale.value
        t0mode = False if self.t0mode.value is None else self.t0mode.value
        try:
            scale = self.GANTT_SCALES[scale_key]
        except KeyError as exc:
            raise ValueError(f"Unknown scale '{scale_key}'") from exc

        if ptype == "r" or ptype == "rg" or ptype == "g":
            project.make_svg_for_resources(
                start=self.start.value,
                end=self.stop.value,
                filename=filename,
                today=self.today.value,
                resources=[res.gantt_object for res in self.pdata.reslist],
                one_line_for_tasks=(ptype == "r"),
                show_title=show_title,
                show_conflicts=show_conflicts,
                offset=offset,
                t0mode=t0mode,
                macro_mode=(ptype == "g"),
                resource_on_left=True,
                scale=scale,
                tu_width=tu_width,
                tu_fraction=tu_fraction,
            )
        elif ptype == "t" or ptype == "m":
            project.make_svg_for_tasks(
                start=self.start.value,
                end=self.stop.value,
                filename=filename,
                today=self.today.value,
                scale=scale,
                t0mode=t0mode,
                macro_mode=(ptype == "m"),
                tu_width=tu_width,
                tu_fraction=tu_fraction,
            )
        else:
            raise ValueError(f"Invalid planning type '{ptype}'")

    def update_project_choices(self, force=False):
        """Update task choices"""
        if self.pdata is None:
            return
        available_choices = self.pdata.project_choices(force)
        self.projects.choices = {
            key: val for key, val in available_choices.items() if key is not None
        }

        if self.projects.value is None:
            return
        project_keys = self.projects.choice_keys
        for project in self.projects.value:
            if project not in project_keys:
                self.projects.value.remove(project)


class AbstractTaskData(AbstractDurationData):
    """Abstract Task data set"""

    def __init__(self, pdata, name=None, fullname=None):
        super().__init__(pdata, name, fullname)
        self.depends_on = DataItem[list[str]](self, "depends_on", DTypes.LIST, None)
        # self.percent_done = DataItem[int](self, "percent_done", DTypes.INTEGER, None)
        self.task_number = DataItem[str](self, "task_number", DTypes.TEXT, None)
        self.depends_on_task_number = DataItem[list[str]](
            self,
            "depends_on_task_number",
            DTypes.LIST,
            value=None,
            # choices=[(self.task_number.value, self.name.value)],
            # default_choice_mode=DefaultChoiceMode.NONE,
        )
        self.update_project_choice()

    def duplicate(self):
        new_item = super().duplicate()
        new_item.task_number.value = None
        return new_item

    def _init_from_element(self, element):
        """Init instance from XML element"""
        super()._init_from_element(element)
        self.depends_on: DataItem[list[str]] = self.get_list("depends_on")
        # self.percent_done: DataItem[int] = self.get_int("percent_done")
        self.depends_on_task_number = DataItem[list[str]](
            self,
            "depends_on_task_number",
            DTypes.LIST,
            value=None,
            # choices=[(self.task_number.value, self.name.value)],
            # default_choice_mode=DefaultChoiceMode.NONE,
        )
        self.update_project_choice()

    def get_attrib_names(self):
        """Return attribute names"""
        return super().get_attrib_names() + ["depends_on", "percent_done"]

    def process_gantt(self):
        """Create or update Gantt objects and add them to dictionaries"""
        task: gantt.Task = self.gantt_object
        if self.pdata.all_tasks:
            # Hopefully, dictionaries are officially ordered since Python 3.7:
            prevtask = self.pdata.all_tasks[list(self.pdata.all_tasks.keys())[-1]]
            # No need to check if last task is related (same resource or no resource)
            # because model data is supposed to be valid at this stage:

            if task.depends_on is not None and len(task.depends_on) > 0:

                # Task can't be started before dep's last end
                min_start_date = task.depends_on[0].end_date()
                for dep in task.depends_on:
                    if dep.end_date() is not None and dep.end_date() < min_start_date:
                        min_start_date = dep.end_date()
                if min_start_date is not None and (
                    task.start is None or task.start < min_start_date
                ):
                    task.start = min_start_date

            elif task.start is None and prevtask is not None:

                if prevtask.stop is not None:
                    task.start = prevtask.stop
                elif prevtask.duration is not None and prevtask.start is not None:
                    # delta = datetime.timedelta(days=prevtask.duration)
                    # task.start = prevtask.start + delta
                    task.start = prevtask.end_date()

                if task.start:
                    while task.non_working_day(task.start):
                        task.start += datetime.timedelta(days=1)

                if task.depends_on is None:
                    task.depends_on = []

        proj_id = self.project.value
        if proj_id not in self.pdata.all_projects:
            self.pdata.process_gantt()
        proj_id = self.project.value
        self.pdata.all_projects[proj_id].add_task(task)
        self.pdata.all_tasks[self.id.value] = task

    def update_depends_on(self):
        """Update depends_on attribute of Gantt task"""
        task = self.pdata.all_tasks[self.id.value]
        if self.depends_on.value is not None:
            task.add_depends(
                [
                    task
                    for tskdata_id, task in self.pdata.all_tasks.items()
                    if tskdata_id in self.depends_on.value
                ]
            )

    def update_depends_on_from_task_number(self):
        if self.depends_on_task_number.value is None:
            return
        wrong_values = []
        new_values = []
        for value in self.depends_on_task_number.value:
            other_task = self.pdata.tsk_num_to_tsk.get(value, None)
            if (
                other_task is None
                or other_task is self
                or (
                    other_task.depends_on_task_number.value is not None
                    and self.task_number.value
                    in other_task.depends_on_task_number.value
                )
            ):
                wrong_values.append(value)
                continue
            if not other_task.has_named_id:
                old_id = other_task.id.value
                new_id = other_task.create_id()
                self.pdata.all_tasks[new_id] = self.pdata.all_tasks.pop(old_id)
                other_task.id.value = new_id
            new_values.append(other_task.id.value)
        self.depends_on.value = new_values
        if wrong_values:
            for value in wrong_values:
                self.depends_on_task_number.value.remove(value)

    def update_depends_on_from_ids(self):
        if self.depends_on.value is None:
            return
        self.depends_on_task_number.value = []
        for i, t_id in enumerate(self.depends_on.value):
            data: AbstractTaskData | None = self.pdata.get_data_from_id(t_id)
            if data is self or data is None:
                continue

            self.depends_on_task_number.value.append(data.task_number.value)

            if data.has_named_id:
                continue

            old_id = data.id.value
            new_id = data.create_id()
            self.depends_on.value[i] = new_id
            if old_id not in self.pdata.all_tasks:
                data.process_gantt()
            self.pdata.all_tasks[new_id] = self.pdata.all_tasks.pop(old_id)
            data.id.value = new_id

    def update_task_choices(self, force=False):
        """Update task choices"""
        if self.pdata is not None:
            self.depends_on_task_number.choices = self.pdata.task_choices(force)  # type: ignore

    def update_project_choice(self, force=False):
        """Update task choices"""
        if self.pdata is None:
            return
        available_choices = self.pdata.project_choices(force)
        self.project.choices = available_choices

        project_keys = self.project.choice_keys

        if self.project.value is None:
            return

        if self.project.value not in project_keys:
            self.project.value = None


class TaskModes(Enum):
    """This is the enum for task modes"""

    DURATION = 0
    STOP = 1


class TaskData(AbstractTaskData):
    """Task data set"""

    TAG = "TASK"
    DEFAULT_ICON_NAME = "task.svg"
    READ_ONLY_ITEMS = ("start_calc", "stop_calc", "task_number")
    DEFAULT_ID_PREFIX = "task"

    def __init__(self, pdata, name=None, fullname=None):
        super().__init__(pdata, name, fullname)
        self.start_calc = DataItem(self, "start_calc", DTypes.DATE, None)
        self.stop_calc = DataItem(self, "stop_calc", DTypes.DATE, None)
        self.percent_done = DataItem(self, "percent_done", DTypes.INTEGER, None)
        self.__resids = []

    def _init_from_element(self, element: ET.Element):
        """Init instance from XML element"""
        super()._init_from_element(element)
        self.percent_done = self.get_int("percent_done")

    def is_read_only(self, name):
        """Return True if item name is read-only"""
        if super().is_read_only(name):
            return True
        return (self.has_duration and name == "stop") or (
            self.has_stop and name == "duration"
        )

    def is_mode_switchable(self):
        """Return True if task mode can be switched from one to another"""
        return self.get_mode() is not None and (
            self.has_start or self.start_calc.value is not None
        )

    def get_mode(self):
        """Return task mode"""
        if self.has_duration and not self.has_stop:
            return TaskModes.DURATION
        if not self.has_duration and self.has_stop:
            return TaskModes.STOP
        if self.start_calc.value is not None and self.has_duration:
            return TaskModes.DURATION
        if self.duration is not None and self.stop_calc.value is not None:
            return TaskModes.STOP
        return None

    def set_stop_from_start_duration(self):
        """Set task stop (taking into account week-ends)"""
        self.stop.value = self.gantt_object.end_date()
        if self.start.value is None and self.start_calc.value is not None:
            self.start.value = self.start_calc.value
            self.start_calc.value = None
            self.stop_calc.value = None
        self.duration.value = None

    def set_duration_from_start_stop(self):
        """Set real task duration (taking into account week-ends)"""
        cday = self.start.value or self.start_calc.value
        real_duration = 0
        if cday is None:
            return
        while cday <= self.stop.value:
            if not self.gantt_object.non_working_day(cday):
                real_duration += 1
            cday += datetime.timedelta(days=1)
        self.duration.value = real_duration
        self.stop.value = None

    def set_mode(self, mode):
        """Set task mode"""
        assert isinstance(mode, TaskModes)
        if self.get_mode() is not mode:
            if mode == TaskModes.DURATION:
                self.set_duration_from_start_stop()
            else:
                self.set_stop_from_start_duration()

    def get_attrib_names(self):
        """Return attribute names"""
        return super().get_attrib_names() + ["percent_done"]

    def get_previous(self):
        """Get previous task data"""
        only = self.__resids
        return self.pdata.get_previous_task_data(self.id.value, only)

    def get_next(self):
        """Get next task data"""
        only = self.__resids
        return self.pdata.get_next_task_data(self.id.value, only)

    def is_valid(self, item_name):
        """Check data item values, eventually depending on planning data"""
        if not super().is_valid(item_name):
            return False
        if item_name in ("stop", "duration"):
            if not self.has_stop and not self.has_duration:
                return False
        if self.has_start:
            if self.has_stop:
                if item_name in ("stop", "start"):
                    return self.stop.value >= self.start.value
                return True
            return True
        prev_data = self.get_previous()
        if item_name == "start":
            if prev_data is None:
                return False
            return prev_data.has_duration or prev_data.has_stop
        return True

    def get_resource_ids(self):
        """Get associated resource ids"""
        return self.__resids

    def set_resource_ids(self, resids):
        """Set associated resource data ids"""
        self.__resids = resids

    def iterate_resource_ids(self):
        """Iterate over resource ids"""
        yield from self.__resids

    def is_assigned_to(self, resid):
        """Return True if data is associated to resource id"""
        return resid in self.__resids

    @property
    def no_resource(self):
        """Return True if no resource is associated to task"""
        return len(self.__resids) == 0

    def process_gantt(self):
        """Create or update Gantt objects and add them to dictionaries"""
        # for data in self.pdata.iterate_chart_data():
        #     data.update_project_choices()
        resource_list = [
            resource
            for resource_id, resource in self.pdata.all_resources.items()
            if resource_id in self.__resids
        ]
        percent_done = 0 if self.percent_done.value is None else self.percent_done.value
        project_name = self.project.choices[self.project.value]
        self.gantt_object = gantt.Task(
            self.name.value,
            start=self.start.value,
            stop=self.stop.value,
            duration=self.duration.value,
            percent_done=percent_done,
            resources=resource_list,
            color=self.color.value or DataItem.COLORS["cyan"],
            project=project_name
        )
        super().process_gantt()

    def update_calc_start_end_dates(self):
        """Update calculated start/end dates"""
        self.start_calc.value = self.gantt_object.start_date()
        try:
            self.stop_calc.value = self.gantt_object.end_date()
        except AttributeError:
            self.stop_calc.value = None


class MilestoneData(AbstractTaskData):
    """Milestone data set"""

    TAG = "MILESTONE"
    DEFAULT_ICON_NAME = "milestone.svg"
    READ_ONLY_ITEMS = ("duration", "stop", "task_number")
    DEFAULT_ID_PREFIX = "mile"

    def is_valid(self, item_name):
        """Check data item values, eventually depending on planning data"""
        if not super().is_valid(item_name):
            return False
        if item_name in ("start") and not self.has_start:
            return False
        return True

    def process_gantt(self):
        """Create or update Gantt objects and add them to dictionaries"""
        self.gantt_object = gantt.Milestone(
            self.name.value,
            start=self.start.value,
            color=self.color.value,
        )
        super().process_gantt()


class AbstractVacationData(AbstractDurationData):
    """Abstract class for vacation days"""

    DEFAULT_ICON_NAME = "leave.svg"
    READ_ONLY_ITEMS = ("name", "fullname", "duration", "color", "project")

    def is_valid(self, item_name=None):
        """Check data item values, eventually depending on planning data"""
        if not super().is_valid(item_name):
            return False
        if self.is_not_set_but_required(item_name, "start"):
            return False
        if self.is_set_but_not_expected(item_name, "duration"):
            return False
        if self.has_stop:
            if item_name in ("stop", "start"):
                return self.stop.value >= self.start.value
        return True


class ClosingDayData(AbstractVacationData):
    """Closing day data set"""

    TAG = "CLOSINGDAY"
    DEFAULT_NAME = _("Closing")
    DEFAULT_ID_PREFIX = "closing"

    def process_gantt(self):
        """Create or update Gantt objects and add them to dictionaries"""
        gantt.add_vacations(self.start.value, end_date=self.stop.value)


class LeaveData(AbstractVacationData):
    """Leave data set"""

    TAG = "LEAVE"
    DEFAULT_NAME = _("Leave")

    def __init__(self, pdata, name=None, fullname=None):
        self.DEFAULT_ID_PREFIX = "leave"
        super().__init__(pdata, name, fullname)
        self.__resid = None

    def is_associated_to(self, resid):
        """Return True if data is associated to resource id"""
        return resid == self.__resid

    def get_resource_id(self):
        """Get associated resource id"""
        return self.__resid

    def set_resource_id(self, resid):
        """Set associated resource id"""
        self.__resid = resid

    def process_gantt(self):
        """Create or update Gantt objects and add them to dictionaries"""
        resource = self.pdata.all_resources[self.__resid]
        resource.add_vacations(dfrom=self.start.value, dto=self.stop.value)


class ResourceData(AbstractData):
    """Resource data set"""

    TAG = "RESOURCE"
    DEFAULT_ICON_NAME = "resource.svg"
    READ_ONLY_ITEMS = ("project",)
    DEFAULT_ID_PREFIX = "resource"

    def __init__(self, pdata, name=None, fullname=None):
        super().__init__(pdata, name, fullname)
        self.collapsed = DataItem(self, "collapsed", DTypes.BOOLEAN, None)

    def _init_from_element(self, element):
        """Init instance from XML element"""
        super()._init_from_element(element)
        self.collapsed = self.get_bool("collapsed")

    def get_attrib_names(self):
        """Return attribute names"""
        attrib_names = super().get_attrib_names()
        return attrib_names + ["collapsed"]

    def process_gantt(self):
        """Create or update Gantt objects and add them to dictionaries"""
        self.gantt_object = self.pdata.all_resources[self.id.value] = gantt.Resource(
            self.name.value, self.fullname.value, color=self.color.value
        )


class ProjectData(AbstractData):
    TAG = "PROJECT"
    DEFAULT_ICON_NAME = "project.svg"
    DEFAULT_COLOR = DataItem.COLORS["silver"]
    DEFAULT_NAME = _("Project")
    READ_ONLY_ITEMS = ()
    DEFAULT_ID_PREFIX = "project"

    def __init__(
        self,
        pdata: "PlanningData",
        name: Optional[str] = None,
        fullname: Optional[str] = None,
    ):
        super().__init__(pdata, name, fullname)

        self.color = DataItem[str](self, "color", DTypes.COLOR, self.DEFAULT_COLOR)
        self.show_description = DataItem[bool](
            self, "show_description", DTypes.BOOLEAN, True
        )

        self.description = DataItem[str](self, "description", DTypes.LONG_TEXT, None)

    @property
    def has_named_id(self):
        return True

    def _init_from_element(self, element):
        super()._init_from_element(element)
        self.color: DataItem[str] = self.get_color(self.DEFAULT_COLOR)
        self.description: DataItem[str] = self.get_long_text("description")
        self.show_description: DataItem[bool] = self.get_bool("show_description")

    def get_attrib_names(self):
        attrib_names = super().get_attrib_names()
        return attrib_names + [
            "project_status",
            "advancement_status",
            "description",
            "show_description",
        ]

    def get_project_tasks(self) -> list[TaskData | MilestoneData]:
        """Returns project's tasks"""
        tasks = []
        for task in self.pdata.iterate_task_data():
            if task.project is not None and task.project.value == self.id.value:
                tasks.append(task)
        return tasks


class PlanningData(AbstractData):
    """Planning data set"""

    DEFAULT_NAME = _("All projects")

    def __init__(self, name=None, fullname=None):
        self._default_id = "main_planning"
        super().__init__(self, name, fullname)
        self.all_projects: dict[Optional[str], gantt.Project] = {}
        self.all_resources: dict[str, gantt.Resource] = {}
        self.all_tasks: dict[str, gantt.Task] = {}
        self.filename = None
        self.reslist: list[ResourceData] = []
        self.tsklist: list[AbstractTaskData] = []
        self.tsk_num_to_tsk: dict[str, AbstractTaskData] = {}
        self._tsk_choices: dict[str, str] = {}
        self._projects_choices: dict[str | None, str] = {}
        self.projects: dict[str, ProjectData] = {}
        self.lvelist: list[LeaveData] = []
        self.clolist: list[ClosingDayData] = []
        self.chtlist: list[ChartData] = []
        self.prjlist: list[ProjectData] = []
        self.__lists: tuple[
            list[ResourceData],
            list[LeaveData],
            list[AbstractTaskData],
            list[ClosingDayData],
            list[ChartData],
            list[ProjectData],
        ] = (
            self.reslist,
            self.lvelist,
            self.tsklist,
            self.clolist,
            self.chtlist,
            self.prjlist,
        )
        self.version = DataItem[float](self, "version", DTypes.FLOAT, VERSION)
        self.tu_width = DataItem[float](self, "tu_width", DTypes.FLOAT, 1.0)
        self.tu_fraction = DataItem[bool](self, "tu_fraction", DTypes.BOOLEAN, True)
        gantt.VACATIONS = []
        self.process_gantt()

    @property
    def default_id(self):
        return self._default_id

    def set_filename(self, filename: str):
        """Set planning data XML filename"""
        self.filename = filename
        self.update_chart_names()
        for chart in self.iterate_chart_data():
            chart.set_is_default_name()

    def _init_from_element(self, element: ET.Element):
        """Init instance from XML element"""
        super()._init_from_element(element)

        # Global settings
        self.version = self.get_float("version", VERSION)
        self.tu_width = self.get_float("tu_width", 1.0)
        if self.tu_width.value < 1.0:
            self.tu_width.value = 1.0
        elif self.tu_width.value > 10.0:
            self.tu_width.value = 10.0
        self.tu_fraction = self.get_bool("tu_fraction", True)

        charts_tag = "CHARTS"
        tasks_tag = "TASKS"
        projects_tag = "PROJECTS"
        projects_elt = element.find(projects_tag)
        if projects_elt is not None:
            for elem in projects_elt.findall(ProjectData.TAG):
                project = ProjectData.from_element(self, elem)
                self.add_project(project, None)
        for elem in self.element.find(charts_tag).findall(ChartData.TAG):
            chtdata = ChartData.from_element(self, elem)
            self.add_chart(chtdata)
        tasks_elt = self.element.find(tasks_tag)
        for elem in tasks_elt.findall(ResourceData.TAG):
            resdata = ResourceData.from_element(self, elem)
            resid = resdata.id.value
            self.add_resource(resdata)
            for telem in resdata.element:
                # Tasks attributed to a resource (direct children to RESOURCE)
                if telem.tag == TaskData.TAG:
                    data = TaskData.from_element(self, telem)
                    data.set_resource_ids([resid])
                    self.add_task(data)
                elif telem.tag == LeaveData.TAG:
                    data = LeaveData.from_element(self, telem)
                    data.set_resource_id(resid)
                    self.add_leave(data)
        # Tasks not attributed to a resource (direct children to TASKS)
        for elem in tasks_elt:
            if elem.tag == TaskData.TAG:
                data = TaskData.from_element(self, elem)
                self.add_task(data)
            elif elem.tag == MilestoneData.TAG:
                data = MilestoneData.from_element(self, elem)
                self.add_task(data)
        cdays_elt = self.element.find("CLOSINGDAYS")
        if cdays_elt is not None:
            for elem in cdays_elt.findall(ClosingDayData.TAG):
                data = ClosingDayData.from_element(self, elem)
                self.add_closing_day(data)
        for data in self.iterate_task_data():
            data.update_task_choices()
            data.update_depends_on_from_ids()

    @classmethod
    def from_filename(cls, fname: str):
        """Instantiate data set from XML file"""
        with open(fname, "rb") as fdesc:
            xmlcode = fdesc.read().decode("utf-8")
        instance = cls.from_element(cls(), ET.fromstring(xmlcode))
        if instance.version.value > float(VERSION):
            raise ValueError(_("This file was made with a newer version of PyPlanning"))
        instance.set_filename(fname)
        return instance

    @classmethod
    def merge_files(cls, fnames: list[str], keep_charts = False) -> tuple["PlanningData", list[str]]:
        """Merge multiple plannings files into one planning object"""

        CONFLICT_COLOR = DataItem.COLORS["_merge_warn"]
        warnings = []

        def __validate_value(values, defaultVal, warning=None):
            val = defaultVal
            if len(values) <= 0 or all(values[0] == v for v in values):
                val = values[0]
            else:
                if warning:
                    warnings.append(_(warning))
            return val

        def __is_attr_conflict(mrg, pln, entity, attr):
            mrg_val = getattr(getattr(mrg, attr, None), "value", None)
            pln_val = getattr(getattr(pln, attr, None), "value", None)
            if pln_val is None or pln_val == mrg_val:
                return False
            else:
                warnings.append(
                    _(
                        f"Conflict on %s '%s', attribute '%s'. {'' if attr == 'color' else 'First value encountered was kept.'}"
                        % (entity, pln.name.value, attr)
                    )
                )
                if getattr(mrg, "color", None):
                    mrg.color.value = CONFLICT_COLOR
                return True

        plannings = [cls.from_filename(fname) for fname in fnames]

        merge = PlanningData(__validate_value([p.name.value for p in plannings], _("Merged planning"), "Planning names are different"))

        if any([pln.version.value is None or pln.version.value > float(VERSION) for pln in plannings]):
            return None, [_("Some plannings are made with a newer PyPlanning version")]

        tu_width = 1.0
        tu_fraction = False
        try: # We have to handle lack of these values, because inexistant on ver < 2.1
            tu_width = max([p.tu_width.value for p in plannings])
            tu_fraction = any([p.tu_fraction.value for p in plannings])
        except Exception:
            pass
        merge.tu_width.value = tu_width
        merge.tu_fraction.value = tu_fraction

        res_names = []
        prj_names = []
        tsk_names = []
        tsk_corr = {}  # Links prev task id to new id in merged planning
        tsk_plns = {}  # Links task key to planning filename
        for pln in plannings:

            for pln_clo in pln.iterate_closing_days_data():
                merge.add_closing_day(pln_clo)

            for pln_res in pln.iterate_resource_data():

                if pln_res.name.value is None:
                    continue
                if pln_res.id.value is None:
                    pln_res.id.value = pln_res.create_id()

                mrg_res: ResourceData = None

                if pln_res.name.value in res_names:

                    mrg_res = merge.get_resource_from_name(pln_res.name.value)

                    for attr in ["fullname", "color"]:
                        __is_attr_conflict(mrg_res, pln_res, _("resource"), attr)

                else:

                    mrg_res = ResourceData(merge, pln_res.name.value)

                    mrg_res.fullname.value = pln_res.fullname.value
                    mrg_res.color.value = pln_res.color.value
                    mrg_res.collapsed.value = False

                    merge.add_resource(mrg_res)
                    res_names.append(pln_res.name.value)

            for pln_lve in pln.iterate_leave_data():

                pln_lve_res_id = pln_lve.get_resource_id()
                pln_lve_res = pln.get_resources_from_ids([pln_lve_res_id])[0]
                mrg_res = merge.get_resource_from_name(pln_lve_res.name.value)

                mrg_lve = LeaveData(merge, pln_lve.name.value, pln_lve.fullname.value)
                mrg_lve.start.value = pln_lve.start.value
                mrg_lve.stop.value = pln_lve.stop.value
                mrg_lve.set_resource_id(mrg_res.id.value)
                merge.add_leave(mrg_lve)

            for pln_prj in pln.iterate_project_data():

                if pln_prj.name.value is None:
                    continue

                mrg_prj: ProjectData = None

                if pln_prj.name.value in prj_names:

                    mrg_prj = merge.get_project_from_name(pln_prj.name.value)

                    for attr in ["description", "color"]:
                        __is_attr_conflict(mrg_prj, pln_prj, _("project"), attr)

                else:

                    mrg_prj = ProjectData(merge, pln_prj.name.value)

                    mrg_prj.description.value = pln_prj.description.value
                    mrg_prj.color.value = pln_prj.color.value
                    mrg_prj.show_description.value = True

                    merge.add_project(mrg_prj, None)
                    prj_names.append(pln_prj.name.value)

            for pln_tsk in pln.iterate_task_data():

                if pln_tsk.name.value is None:
                    continue

                mrg_tsk: AbstractTaskData = None
                pln_tsk_key = f"{pln_tsk.name.value}-[{pln_tsk.project.value}]"

                attrs = ["fullname", "color", "start"]
                if isinstance(pln_tsk, TaskData):
                    attrs.extend([ "percent_done", "duration", "stop"])

                pln_tsk_prjname = "<Global>"
                if pln_tsk.project.value is not None:
                    pln_tsk_prjname = pln.get_data_from_id(pln_tsk.project.value).name.value

                # Treat tasks with same name and project in same planning as different tasks (splited in periods and/or resources)
                if pln_tsk_key in tsk_plns.keys() and tsk_plns[pln_tsk_key] == pln.filename:

                    suffix = 2
                    while (
                        f"{pln_tsk.name.value} ({suffix})-[{pln_tsk.project.value}]"
                        in tsk_names
                    ):
                        suffix += 1

                    if suffix == 2:
                        warnings.append(_("Duplicate(s) of element '%s' in project '%s' in the same planning. They were kept and differentiated via suffixes." % (pln_tsk.name.value, pln_tsk_prjname)))

                    pln_tsk_key = f"{pln_tsk.name.value} ({suffix})-[{pln_tsk.project.value}]"
                    pln_tsk.name.value = pln_tsk.name.value + f" ({suffix})"
                    pln_tsk.color.value = CONFLICT_COLOR

                if pln_tsk_key in tsk_names:

                    # Update link dict for dependencies

                    mrg_prj_tasks = []
                    mrg_tsk_id = None
                    if pln_tsk.project.value is None:
                        mrg_prj_tasks = merge.get_global_tasks()
                    else:
                        mrg_prj = merge.get_project_from_name(pln.get_data_from_id(pln_tsk.project.value).name.value)
                        mrg_prj_tasks = mrg_prj.get_project_tasks()

                    for t in mrg_prj_tasks:
                        if t.name.value == pln_tsk.name.value:
                            mrg_tsk_id = t.id.value
                            break

                    mrg_tsk = merge.get_data_from_id(mrg_tsk_id)
                    for attr in attrs:
                        __is_attr_conflict(mrg_tsk, pln_tsk, f"project '{pln_tsk_prjname}', task", attr)

                    # Commented : Task is was being checked for the depends
                    # when it's not in the list of task of the project
                    # tsk_corr[pln_tsk.id.value] = mrg_tsk_id
                    merge.get_data_from_id(mrg_tsk_id).color.value = CONFLICT_COLOR

                    continue

                else:

                    tsk_plns[pln_tsk_key] = pln.filename

                    if isinstance(pln_tsk, TaskData):
                        mrg_tsk = TaskData(merge, pln_tsk.name.value)
                    else:
                        mrg_tsk = MilestoneData(merge, pln_tsk.name.value)

                    for attr in attrs:
                        setattr(mrg_tsk, attr, getattr(pln_tsk, attr))

                    # Update project and resources

                    if pln_tsk.has_project:
                        mrg_tsk.project.value = merge.get_project_from_name(pln.projects[pln_tsk.project.value].name.value).id.value

                    if isinstance(pln_tsk, TaskData) and not pln_tsk.no_resource:

                        pln_tsk_res_ids = pln_tsk.get_resource_ids()
                        mrg_tsk_res_ids = []
                        for pln_res_id in pln_tsk_res_ids:
                            pln_res = pln.get_resources_from_ids([pln_res_id])[0]
                            mrg_res = merge.get_resource_from_name(pln_res.name.value)
                            mrg_tsk_res_ids.append(mrg_res.id.value)
                        mrg_tsk.set_resource_ids(mrg_tsk_res_ids)

                    mrg_tsk.update_project_choice()
                    tsk_names.append(pln_tsk_key)
                    tsk_corr[pln_tsk.id.value] = mrg_tsk.id.value
                    merge.add_task(mrg_tsk)

            # 2nd round: update task dependencies

            for pln_tsk in pln.iterate_task_data():

                if pln_tsk.id.value in tsk_corr:
                    mrg_tsk = merge.get_data_from_id(tsk_corr[pln_tsk.id.value])

                    if pln_tsk.depends_on.value is None:
                        continue

                    for pln_dep_id in pln_tsk.depends_on.value:
                        # Check that the 'id' in depends_on exists
                        # since the field can be set on task without needing a task
                        # with this id declared (it's ignored when the project is loaded)
                        if pln_dep_id in tsk_corr:
                            mrg_dep_tsk = merge.get_data_from_id(tsk_corr[pln_dep_id])
                            if mrg_dep_tsk is not None:
                                if mrg_tsk.depends_on.value is None:
                                    mrg_tsk.depends_on.value = []
                                mrg_tsk.depends_on.value.append(mrg_dep_tsk.id.value)
                            else:
                                warnings.append(
                                    _(
                                        f"Task with %s depends on a none existing one with ID '%s''." % (pln_tsk.name.value, pln_dep_id)
                                    )
                                )

        for t in merge.iterate_task_data():
            t.update_task_choices()
            t.update_depends_on_from_ids()

        merge.update_task_number()

        # Copy charts from the open/first planning file
        if keep_charts:
            first_planning = plannings[0]
            for chart in first_planning.chtlist:
                mrg_chart = ChartData(merge, chart.name.value, chart.fullname.value)
                mrg_chart.start = chart.start
                mrg_chart.stop = chart.stop
                mrg_chart.today = chart.today
                mrg_chart.t0mode = chart.t0mode
                mrg_chart.color = chart.color
                mrg_chart.scale = chart.scale
                mrg_chart.type = chart.type
                mrg_chart.update_project_choices()

                if chart.projects.value is not None:
                    for project_id in chart.projects.value:
                        prj_name = chart.projects.choices[project_id]
                        if prj_name in prj_names:
                            mrg_proj = merge.get_project_from_name(prj_name)
                            if mrg_chart.projects.value is not None:
                                mrg_chart.projects.value.append(mrg_proj.default_id)
                            else:
                                mrg_chart.projects.value = [mrg_proj.default_id]
                merge.add_chart(mrg_chart)


        return merge, warnings

    def to_element(self, parent=None):
        """Serialize model to XML element"""
        base_elt = ET.Element("PLANNING", attrib=self.get_attrib_dict())
        base_elt.set("version", VERSION)
        base_elt.set("tu_width", str(self.tu_width.value))
        base_elt.set("tu_fraction", str(self.tu_fraction.value))
        charts_elt = ET.SubElement(base_elt, "CHARTS")
        for data in self.iterate_chart_data():
            data.to_element(charts_elt)
        tasks_elt = ET.SubElement(base_elt, "TASKS")
        for resdata in self.iterate_resource_data():
            res_elt = resdata.to_element(tasks_elt)
            for data in self.iterate_task_data(only=[resdata.id.value]):
                data.to_element(res_elt)
            for data in self.iterate_leave_data(only=resdata.id.value):
                data.to_element(res_elt)
        for data in self.iterate_task_data(only=[]):
            data.to_element(tasks_elt)
        cdays_elt = ET.SubElement(base_elt, "CLOSINGDAYS")
        for data in self.iterate_closing_days_data():
            data.to_element(cdays_elt)
        projects_elt = ET.SubElement(base_elt, "PROJECTS")
        for project in self.iterate_project_data():
            project.to_element(projects_elt)
        return base_elt

    def to_text(self):
        """Serialize model to XML, indent and return text string"""
        tree = ET.ElementTree(self.to_element())
        ET.indent(tree)
        strio = StringIO()
        tree.write(strio, encoding="unicode")
        text = strio.getvalue()
        strio.close()
        return text

    def to_filename(self, fname: str):
        """Serialize model to XML file"""
        self.set_filename(fname)
        tree = ET.ElementTree(self.to_element())
        ET.indent(tree)
        tree.write(fname, encoding="utf-8")

    def move_data(self, data_id, delta_index):
        """Move task/resource/chart up/down"""
        data = self.get_data_from_id(data_id)
        dlist = None
        for dlist in self.__lists:
            if data in dlist:
                break
        if dlist is None:
            return

        index = dlist.index(data)
        if index + delta_index >= len(dlist) or index + delta_index < 0:
            return
        dlist[index], dlist[index + delta_index] = (
            dlist[index + delta_index],
            dlist[index],
        )
        if isinstance(data, AbstractTaskData):
            self.update_task_number(max(0, index + delta_index - 1), True)

    def remove_data(self, data_id):
        """Remove either task/resource/chart data"""
        data = self.get_data_from_id(data_id)
        for dlist in self.__lists:
            if data in dlist:
                index = dlist.index(data)
                dlist.pop(index)
                if isinstance(data, AbstractTaskData):
                    self.update_task_number(index)
                break
        else:
            raise ValueError("Data not found in model")

    def get_previous_task_data(self, data_id, only):
        """Return previous task data"""
        prev_data = None
        for data in self.iterate_task_data(only=only):
            if data.id.value == data_id:
                break
            prev_data = data
        return prev_data

    def get_next_task_data(self, data_id, only):
        """Return next task data"""
        next_data = None
        prev_data_id = None
        for data in self.iterate_task_data(only=only):
            if prev_data_id == data_id:
                next_data = data
                break
            prev_data_id = data.id.value
        return next_data

    def get_task_project_names(self):
        """Return all task project names"""
        pnames = []
        for data in self.iterate_task_data():
            if data.has_project:
                pnames.append(data.project.value)
        return tuple(set(pnames))

    def get_global_tasks(self) -> list[TaskData | MilestoneData]:
        """Returns tasks without linked project"""
        tasks = []
        for task in self.pdata.iterate_task_data():
            if task.project is None or task.project.value is None:
                tasks.append(task)
        return tasks

    def iterate_chart_data(self) -> Generator[ChartData, None, None]:
        """Iterate over chart data dictionary items"""
        yield from self.chtlist

    def iterate_resource_data(self) -> Generator[ResourceData, None, None]:
        """Iterate over resource data dictionary items"""
        yield from self.reslist

    def iterate_project_data(self) -> Generator[ProjectData, None, None]:
        """Iterate over project data dictionary items"""
        yield from self.prjlist

    def iterate_task_data(
        self, only=None,
    ) -> Generator[TaskData | MilestoneData, None, None]:
        """Iterate over task data dictionary items"""
        for data in self.tsklist:
            if only is None:
                yield data
            elif isinstance(data, MilestoneData):
                if only == []:
                    yield data
            else:
                if only == []:
                    if data.no_resource:
                        yield data
                else:
                    for resid in only:
                        if data.is_assigned_to(resid):
                            yield data
                            continue

    def iterate_leave_data(self, only=None) -> Generator[LeaveData, None, None]:
        """Iterate over leave data dictionary items"""
        for data in self.lvelist:
            if only is None or data.is_associated_to(only):
                yield data

    def iterate_closing_days_data(self) -> Generator[ClosingDayData, None, None]:
        """Iterate over closing days data dictionary items"""
        yield from self.clolist

    def iterate_all_data(self) -> Generator[AbstractData, None, None]:
        """Iterate over all data dictionary items"""
        for dlist in self.__lists:
            yield from dlist

    def get_data_from_id(self, data_id) -> Optional[AbstractData]:
        """Return data (chart, resource, task, leave) from id"""
        for data in self.iterate_all_data():
            if data.id.value == data_id:
                return data
        return None

    def get_resources_from_ids(self, resids) -> list[ResourceData]:
        """Return resource list from resource data id list"""
        if resids:
            return [
                resdata
                for resdata in self.iterate_resource_data()
                if resdata.id.value in resids
            ]
        return []

    def get_resource_from_name(self, resname) -> Optional[ResourceData]:
        """Return resource data from name"""
        for data in self.iterate_resource_data():
            if data.name.value == resname:
                return data
        return None

    def get_project_from_name(self, prjname) -> Optional[ResourceData]:
        """Return project data from name"""
        for data in self.iterate_project_data():
            if data.name.value == prjname:
                return data
        return None

    def get_all_ids(self) -> list[str]:
        """Retrieve all existing ids of the planning"""
        return [data.id.value for data in self.iterate_all_data() if data.id.value is not None]

    def regenerate_project_id(self, project_id, forbidden_ids=None) -> str:
        """Regenerate new project id outside of forbidden ones and update its tasks"""
        project = self.get_data_from_id(project_id)
        if project is self or project is None:
            return None

        new_id = self.create_id("project", forbidden_ids)

        project.id.value = new_id
        if project_id in self.all_projects.keys():
            self.all_projects[new_id] = self.all_projects.pop(project_id)
        self.projects[new_id] = self.projects.pop(project_id)

        for t in self.iterate_task_data():
            if t.project.value is None:
                continue
            if t.project.value == project_id:
                t.project.value = new_id

        return new_id

    def regenerate_task_id(self, task_id, forbidden_ids=None) -> str:
        """Regenerate new task id outside of forbidden ones and update its dependancies"""
        task = self.get_data_from_id(task_id)
        if task is self or task is None:
            return None

        new_id = self.create_id("task", forbidden_ids)

        task.id.value = new_id
        if task_id in self.all_tasks.keys():
            self.all_tasks[new_id] = self.all_tasks.pop(task_id)

        # Update dependancies
        for t in self.iterate_task_data():
            if t.depends_on.value is None:
                continue
            if task_id in t.depends_on.value:
                t.depends_on.value[t.depends_on.value.index(task_id)] = new_id

        return new_id

    @staticmethod
    def __append_or_insert(
        dlist: list[AbstractDataT], index: Optional[int], data: AbstractDataT
    ):
        """Append or insert data to list"""
        if index is None:
            dlist.append(data)
        else:
            dlist.insert(index + 1, data)

    def add_resource(
        self, data: ResourceData, after_data: Optional[AbstractData] = None
    ):
        """Add resource to planning"""
        index = None
        if isinstance(after_data, TaskData):
            resids = after_data.get_resource_ids()
            if resids:
                index = self.reslist.index(self.get_data_from_id(resids[0]))
        elif isinstance(after_data, ResourceData):
            index = self.reslist.index(after_data)
        self.__append_or_insert(self.reslist, index, data)

    def add_task(
        self, data: AbstractTaskData, after_data: Optional[AbstractData] = None
    ):
        """Add task/milestone to planning"""
        index = None
        task_number_index = None
        if isinstance(after_data, AbstractTaskData):
            index = task_number_index = self.tsklist.index(after_data)
        elif isinstance(after_data, ResourceData):
            # Sum all task indexes for all resources before:
            resids = []
            for res in self.reslist:
                if res is after_data:
                    break
                resids.append(res.id.value)
            index = -1
            for resid in resids:
                for _task in self.iterate_task_data(only=[resid]):
                    index += 1
            task_number_index = index + 1
        self.__append_or_insert(self.tsklist, index, data)
        self.update_task_number(task_number_index)

    def add_project(self, project: ProjectData, after_data: Optional[ProjectData]):
        self.projects[str(project.id.value)] = project
        self.all_projects[str(project.id.value)] = gantt.Project(
            name=str(project.name.value),
            color=project.color.value,
            show_description=bool(project.show_description.value),
        )
        index = self.prjlist.index(after_data) if after_data else None
        self.__append_or_insert(self.prjlist, index, project)

    def task_choices(self, force=False) -> list[dict[str, str]]:
        if force or len(self._tsk_choices.keys()) != len(self.tsklist):
            self._tsk_choices = {
                str(data.task_number.value): str(data.name.value)
                for data in self.iterate_task_data()
            }
        return self._tsk_choices

    def project_choices(self, force=False) -> list[dict[str | None, str]]:
        if force or (len(self.projects.keys()) + 1) != len(
            self._projects_choices.keys()
        ):
            self._projects_choices = {None: ""}
            for proj in self.prjlist:
                if proj.id.value is not None:
                    self._projects_choices[proj.id.value] = str(proj.name.value)
        return self._projects_choices

    def update_task_number(self, index: Optional[int] = None, force=False):
        """Update task number. If None, only the last one is updated,
        else all tasks from index are updated. Also updates all the
        "depends_on_task_number" dataitems with the new task numbers.

        Args:
            index: index of the task to update. Defaults to None.
        """
        if index is None:
            data = self.tsklist[-1]
            data.task_number.value = str(len(self.tsklist))
            self.tsk_num_to_tsk[data.task_number.value] = data
        else:
            for i, data in enumerate(self.tsklist[index:], start=index + 1):
                str_idx = str(i)
                data.task_number.value = str(str_idx)
                self.tsk_num_to_tsk[str_idx] = data

        for data in self.iterate_task_data():
            data.update_depends_on_from_ids()
            data.update_task_choices(force=force)

    def add_leave(self, data: LeaveData, after_data: Optional[AbstractData] = None):
        """Add resource leave to planning"""
        index = None
        if isinstance(after_data, LeaveData):
            index = self.lvelist.index(after_data)
        self.__append_or_insert(self.lvelist, index, data)

    def add_closing_day(
        self, data: ClosingDayData, after_data: Optional[AbstractData] = None
    ):
        """Add closing day to planning"""
        index = None
        if isinstance(after_data, ClosingDayData):
            index = self.clolist.index(after_data)
        self.__append_or_insert(self.clolist, index, data)

    def add_chart(self, data: ChartData, after_data: Optional[AbstractData] = None):
        """Add chart to planning"""
        index = None
        if isinstance(after_data, ChartData):
            index = self.chtlist.index(after_data)
        self.__append_or_insert(self.chtlist, index, data)
        self.update_chart_names()

    def update_chart_names(self):
        """Update chart names"""
        if self.filename is None:
            return

        xml_filename = self.filename
        for index, data in enumerate(self.iterate_chart_data(), start=1):
            data.set_chart_filename(xml_filename, index)

    @property
    def chart_filenames(self) -> list[str]:
        """Return chart filenames"""
        return [str(data.fullname.value) for data in self.iterate_chart_data()]

    def toggle_tu_fraction(self, state: bool):
        """Toggle display of time unit fractions on charts"""
        assert isinstance(state, bool)
        self.tu_fraction.value = state
        self.generate_charts()

    def process_gantt(self):
        """Create or update Gantt objects and add them to dictionaries"""
        self.all_projects.clear()
        self.all_resources.clear()
        self.all_tasks.clear()
        mainproj = gantt.Project(
            name=self.name.value,
            color=self.color.value,
        )
        self.all_projects[None] = mainproj
        for project in self.iterate_project_data():
            if project.id.value is None:
                continue
            self.all_projects[project.id.value] = gantt.Project(
                name=str(project.name.value),
                color=project.color.value,
                description=project.description.value or "",
                show_description=bool(project.show_description.value),
            )
        for data in self.iterate_all_data():
            data.process_gantt()
        for data in self.iterate_task_data():
            data.update_depends_on()
        for proj_id, project in self.all_projects.items():
            if proj_id is not None:
                mainproj.add_task(project)
        for data in self.iterate_chart_data():
            data.update_project_choices()

    def update_task_calc_dates(self):
        """Update task calculated start/end dates"""
        for data in self.iterate_task_data():
            if isinstance(data, TaskData):
                data.update_calc_start_end_dates()

    def generate_charts(self, one_line_for_tasks=True):
        """Generate charts"""
        self.process_gantt()
        for chart in self.iterate_chart_data():
            proj_ids = chart.projects.get_choices_values()
            wrong_proj_id = []
            if not proj_ids:
                project = self.all_projects[None]
            else:
                # transparent color and no name
                project = gantt.Project(name="", color="#FFFFFFFF")
                for proj_id in proj_ids:
                    proj = self.all_projects.get(proj_id, None)
                    if proj is None:
                        wrong_proj_id.append(proj_id)
                        continue
                    project.add_task(proj)
                    # for task in proj.get_tasks():
                    #     project.add_task(task)
            chart.make_svg(
                project,
                one_line_for_tasks,
                tu_width=self.tu_width.value,
                tu_fraction=self.tu_fraction.value,
            )

            # if wrong_pnames and chart.projects.value is not None:
            #     for pname in wrong_pnames:
            #         chart.projects.value.remove(pname)
        self.update_task_calc_dates()

    def generate_current_chart(self, index: int, one_line_for_tasks=True):
        """Refresh current chart.

        Args:
            index: The index of the chart to refresh.
            one_line_for_tasks: If True, draw tasks on one line.
        """
        if len(self.chtlist) == 0:
            return
        self.process_gantt()
        chart = self.chtlist[index]
        pnames = chart.projects.value
        wrong_pnames = []
        if not pnames:
            project = self.all_projects[None]
        else:
            # transparent color and no name
            project = gantt.Project(name="", color="#FFFFFFFF")
            for pname in pnames:
                proj = self.all_projects.get(pname, None)
                if proj is None:
                    wrong_pnames.append(pname)
                    continue
                project.add_task(proj)

        chart.make_svg(
            project,
            one_line_for_tasks,
            tu_width=self.tu_width.value,
            tu_fraction=self.tu_fraction.value,
        )
        self.update_task_calc_dates()
