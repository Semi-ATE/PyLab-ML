#!/usr/bin/env python3
"""
get project infos from the harness/project_info.yaml file
and set the environment variable.


"""
import os
from pathlib import Path
import yaml
from ate_common.logger import (LogLevel)


class Project_Info:

    def __init__(self, filename, logger, path= "harness/project_info.yaml" ):
        """
        Get project infos from the harness/project_info.yaml file.

        and set the environment variable.
        """
        self.logger = logger
        self.hpath = os.path.join(str(Path(filename).parent.parent.parent.parent), os.path.dirname(path))
        project_file = os.path.join(self.hpath, os.path.basename(path))

        project_info = ""
        if  os.path.isfile(project_file):
            with open(project_file, 'r', encoding='utf-8') as file:
                project_info = yaml.safe_load(file)
        else:
            self.logger.log_message(LogLevel.Error(), f'Project_Info: {project_file} not defined')
        for name in project_info:
            value = project_info[name]

            if type(value) is dict and 'PROJECT' in project_info and project_info['PROJECT'] in value:
                value = value[project_info['PROJECT']]
            if type(value) is dict and 'VERSION' in project_info and project_info['VERSION'] in value:
                value = value[project_info['VERSION']]
            value = self.replace_variables(value)
            if value is not None:
                os.environ[name] = value
            setattr(self, name, value)
            
            
    def replace_variables(self, value):
        """
        Check if valuestr has environment-variables starts with $, or valuestr has path-value like './'.

        If yes than replace environment-variables with its value,

        """
        valuestr = value
        if type(value) is str and value.find('$') > -1:   # find environment variables inside the value?
            tmp = value.split('/')
            nvalue = ''
            for s in tmp:
                if s.find('$') == 0:
                    env = s[1:]
                    s = os.environ.get(env)
                if s is None:
                    self.logger.log_message(LogLevel.Error(), f'Project_Info: environment {env} not defined')
                    s = ''
                nvalue += s + '/'
            if nvalue != '':
                valuestr = nvalue[:-1]
        elif type(value) is str and value.find('.') > -1:
            valuestr = value.replace('./', self.hpath)
        return valuestr