#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Provides functions for creating a python classes from the cp2k_input.xml
file.
"""

import xml.etree.cElementTree as cElementTree
from pycp2k import utilities
import textwrap


#===============================================================================
def validify_section(string):
    """Modifies the section name so that it can be used as a valid attribute
    name in a python class.
    """
    original = string
    changed = False

    if "-" in string:
        changed = True
        string = string.replace("-", "_")

    if "+" in string:
        changed = True
        string = string.replace("+", "PLUS")

    if string[0].isdigit():
        changed = True
        string = "NUM" + string

    if changed:
        print "    Section " + original + " replaced with " + string
    return string


#===============================================================================
def validify_keyword(string):
    """Modifies the keyword name so that it can be used as a valid attribute
    name in a python class.
    """
    original = string
    changed = False

    if "-" in string:
        changed = True
        string = string.replace("-", "_")

    if "+" in string:
        changed = True
        string = string.replace("+", "PLUS")

    if string[0].isdigit():
        changed = True
        string = "NUM" + string

    if changed:
        print "    Keyword " + original + " replaced with " + string

    string = string.capitalize()
    return string


#===============================================================================
def recursive_class_creation(section, level, class_dictionary, version_dictionary):
    """Recursively goes throught the .xml file created by cp2k --xml command
    and creates a python class for each section. Keywords, default keywords,
    section parameters and subsections are stored as attributes.
    """
    default_keywords = {}
    repeated_default_keywords = {}
    keywords = {}
    repeated_keywords = {}
    subsections = {}
    repeated_subsections = {}
    repeated_aliases = {}
    aliases = {}
    attributes = ["Default_keyword", "Section_parameters"]
    inp_name = ""

    # Initial string for each section of the class
    docstring = ""
    properties = ""
    setters = ""
    public = "    def __init__(self):\n"
    private = ""
    class_subsections = ""
    functions = "\n"

    # The root with tag CP2K_INPUT doesn't have a name. It is hardcoded here.
    sectionname = section.find("NAME")
    if sectionname is None:
        class_name = "_CP2K_INPUT"
        inp_name = "CP2K_INPUT"
    else:
        class_name = sectionname.text
        inp_name = class_name
        class_name = validify_section(class_name)
        class_name = "_" + class_name.lower()

    # Start writing class body
    class_body = ""
    section_description = section.find("DESCRIPTION")
    if section_description is not None and section_description.text is not None:
        docstring += "    \"\"\"\n"
        for line in textwrap.wrap(section_description.text):
            docstring += "    " + line + "\n"
        docstring += "    \"\"\"\n"
    else:
        docstring += "    \"\"\"\"\"\"\n"

    #---------------------------------------------------------------------------
    # Create attribute for section parameter
    section_parameters = section.find("SECTION_PARAMETERS")
    if section_parameters is not None:
        public += "        self.Section_parameters = None\n"

        # Write the description for the section parameter
        description = section_parameters.find("DESCRIPTION").text
        public += "        \"\"\"\n"
        if description is not None:
            for line in textwrap.wrap(description):
                public += "        " + line + "\n"
        else:
            public += "\n"

        # If the values are enumerated, document the possible values
        data_type = section_parameters.find("DATA_TYPE")
        if data_type.get("kind") == "keyword":
            public += "\n        Available values:\n"
            enumerations = data_type.find("ENUMERATION")
            for enum in enumerations.findall("ITEM"):
                public += "            " + enum.find("NAME").text + "\n"
                enum_description = enum.find("DESCRIPTION").text
                if enum_description is not None:
                    for line in textwrap.wrap(enum_description):
                        public += "                " + line + "\n"

        public += "        \"\"\"\n"

    #---------------------------------------------------------------------------
    # Create attribute for all the keywords
    for keyword in section.findall("KEYWORD"):

        # First find out the default name and whether the attribute is visible or not
        default_name = ""
        visible = True
        for keyname in keyword.findall("NAME"):
            keytype = keyname.get("type")
            name = keyname.text
            newname = validify_keyword(name)
            if keytype == "default":
                default_name = newname
                if name.startswith("__"):
                    visible = False

        # Now store the keywords as class attributes
        if visible:
            for keyname in keyword.findall("NAME"):
                name = keyname.text
                newname = validify_keyword(name)

                # Write the description for the keyword
                description = keyword.find("DESCRIPTION").text
                desc_text = "        \"\"\"\n"
                if description is not None:
                    for line in textwrap.wrap(description):
                        desc_text += "        " + line + "\n"
                else:
                    desc_text += "\n"

                # If the values are enumerated, document the possible values
                data_type = keyword.find("DATA_TYPE")
                if data_type.get("kind") == "keyword":
                    desc_text += "\n        Available values:\n"
                    enumerations = data_type.find("ENUMERATION")
                    for enum in enumerations.findall("ITEM"):
                        desc_text += "            " + enum.find("NAME").text + "\n"
                        enum_description = enum.find("DESCRIPTION").text
                        if enum_description is not None:
                            for line in textwrap.wrap(enum_description):
                                desc_text += "                " + line + "\n"
                desc_text += "        \"\"\"\n"

                # Create original attribute for the default keyname
                if newname == default_name:

                    # Special case for repeateable keywords.
                    if keyword.get("repeats") == "yes":
                        public += "        self." + newname + " = []\n"
                        public += desc_text
                        repeated_keywords[newname] = name
                    else:
                        public += "        self." + newname + " = None\n"
                        public += desc_text
                        keywords[newname] = name

                # Create properties for aliases
                else:
                    if keyword.get("repeats") == "yes":
                        public += "        self." + newname + " = self." + default_name + "\n"
                        repeated_aliases[newname] = default_name
                    else:
                        aliases[newname] = default_name
                        properties += ("\n    @property\n"
                                       "    def " + newname + "(self):\n"
                                       "        \"\"\"\n"
                                       "        See documentation for " + default_name + "\n"
                                       "        \"\"\"\n"
                                       "        return self." + default_name + "\n")
                        setters += ("\n    @" + newname + ".setter\n"
                                    "    def " + newname + "(self, value):\n"
                                    "        self." + default_name + " = value\n")

    #---------------------------------------------------------------------------
    # Create a class attribute for all DEFAULT_KEYWORDS
    default_keyword = section.find("DEFAULT_KEYWORD")
    if default_keyword is not None:
        # Special case for repeateable default_keywords. Create a dictionary of the
        # keyword and add a function for creating them.
        name = default_keyword.find("NAME").text
        newname = validify_keyword(name)

        # Write the description for the keyword
        description = default_keyword.find("DESCRIPTION").text
        desc_text = "        \"\"\"\n"
        if description is not None:
            for line in textwrap.wrap(description):
                desc_text += "        " + line + "\n"
        else:
            desc_text += "\n"

        # If the values are enumerated, document the possible values
        data_type = default_keyword.find("DATA_TYPE")
        if data_type.get("kind") == "keyword":
            desc_text += "        AVAILABLE VALUES:\n"
            enumerations = data_type.find("ENUMERATION")
            for enum in enumerations.findall("ITEM"):
                desc_text += "            " + enum.find("NAME").text + "\n"
                enum_description = enum.find("DESCRIPTION").text
                if enum_description is not None:
                    for line in textwrap.wrap(enum_description):
                        desc_text += "                " + line + "\n"

        desc_text += "        \"\"\"\n"

        if default_keyword.get("repeats") == "yes":
            public += "        self." + newname + " = []\n"
            public += desc_text
            repeated_default_keywords[newname] = name
        else:
            public += "        self." + newname + " = None\n"
            public += desc_text
            default_keywords[newname] = name

    #---------------------------------------------------------------------------
    # Create attribute for each subsection
    for subsection in section.findall("SECTION"):
        member_class_name = recursive_class_creation(subsection, level+1, class_dictionary, version_dictionary)
        member_name = subsection.find("NAME").text
        member_name = member_name.replace("-", "_")
        member_name = member_name.replace("+", "PLUS")
        if member_name[0].isdigit():
            member_name = "_" + member_name

        # Special case for repeateable sections. Create a dictionary of the
        # subsections and add a function for creating them.
        if subsection.get("repeats") == "yes":
            class_subsections += "        self." + member_name + "_list = []\n"
            repeated_subsections[member_name] = member_class_name
            attributes.append(member_name + "_list")
        else:
            class_subsections += "        self." + member_name + " = " + member_class_name + "()\n"
            subsections[member_name] = subsection.find("NAME").text

    #---------------------------------------------------------------------------
    # Write a list of the stored variable names
    private += "        self._name = \"" + str(inp_name) + "\"\n"
    private += "        self._keywords = " + str(keywords) + "\n"
    private += "        self._repeated_keywords = " + str(repeated_keywords) + "\n"
    private += "        self._default_keywords = " + str(default_keywords) + "\n"
    private += "        self._repeated_default_keywords = " + str(repeated_default_keywords) + "\n"
    private += "        self._subsections = " + str(subsections) + "\n"
    private += "        self._repeated_subsections = " + str(repeated_subsections) + "\n"
    private += "        self._aliases = " + str(aliases) + "\n"
    private += "        self._repeated_aliases = " + str(repeated_aliases) + "\n"
    private += "        self._attributes = " + str(attributes) + "\n"
    
    #---------------------------------------------------------------------------
    # Write a function for adding repeateable sections
    for repeated in repeated_subsections.iteritems():
        attribute_name = repeated[0]
        attribute_class_name = repeated[1]
        functions += ("    def " + attribute_name + "_add(self, section_parameters=None):\n"
                      "        new_section = " + attribute_class_name + "()\n"
                      "        if section_parameters is not None:\n"
                      "            if hasattr(new_section, 'Section_parameters'):\n"
                      "                new_section.Section_parameters = section_parameters\n"
                      "        self." + attribute_name + "_list.append(new_section)\n"
                      "        return new_section\n\n")

    # Write a function for printing original CP2K input files
    functions += ("    def print_input(self, level):\n"
                  "        return printable.print_input(self, level)\n")

    #---------------------------------------------------------------------------
    # The class names are not unique. Use numbering to identify classes.
    exists = False
    version_number = version_dictionary.get(class_name)
    if version_number is None:
        version_dictionary[class_name] = 1
        class_dictionary[class_name+str(1)] = docstring + public + class_subsections + private + functions + properties + setters
        return class_name+str(1)

    for version in range(version_number):
        old_class_body = class_dictionary[class_name+str(version + 1)]
        if old_class_body == class_body:
            exists = True
            version_number = version + 1
            break

    if not exists:
        version_dictionary[class_name] = version_number + 1
        class_dictionary[class_name+str(version_number + 1)] = docstring + public + class_subsections + private + functions + properties + setters
        return class_name + str(version_number + 1)
    else:
        return class_name + str(version_number)


#===============================================================================
def main(xml_path):
    """Parses the classes and saves them to the package directory as
    parsedclasses.py.
    """
    # Start parsing here
    utilities.print_subtitle("CREATING INPUT STRUCTURE...")
    tree = cElementTree.parse(xml_path)
    root = tree.getroot()
    module_header = (
        "#! /usr/bin/env python\n"
        "# -*- coding: utf-8 -*-\n\n"
        "\"\"\"This module holds all the classes parsed from xml file created with command\ncp2k --xml\"\"\"\n\n"
        "from pycp2k.printable import printable\n"
    )
    class_dictionary = {}
    version_dictionary = {}
    recursive_class_creation(root, 0, class_dictionary, version_dictionary)

    # Write one module containing all the parsed classes.
    with open('pycp2k/parsedclasses.py', 'w') as file:
        file.write(module_header)
        for class_name, class_body in class_dictionary.iteritems():
            class_body_header = (
                "\n\nclass " + class_name + "(printable):\n"
            )
            file.write(class_body_header.encode('utf8'))
            file.write(class_body.encode('utf8'))

    return True

# Run main function by default
if __name__ == "__main__":
    main()
