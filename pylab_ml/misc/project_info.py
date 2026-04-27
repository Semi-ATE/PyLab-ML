#!/usr/bin/env python3
"""
get project infos from the harness/project_info.yaml file
and set the environment variable.


"""
import os
from pathlib import Path
import yaml


class Project_Info:

    def __init__(self, filename):
        """
        Get project infos from the harness/project_info.yaml file.

        and set the environment variable.
        """
        
        project_file = os.path.join(str(Path(filename).parent.parent.parent.parent), "harness", "project_info.yaml")
        
        if  os.path.isfile(project_file):
            with open(project_file, 'r', encoding='utf-8') as file:
                project_info = yaml.safe_load(file)
        for name in project_info:
            value = project_info[name]
            if type(value) is dict and 'VERSION' in project_info and project_info['VERSION'] in value:
                value = value[project_info['VERSION']]
            if value is not None:
                os.environ[name] = value
            setattr(self, name, value)