# coding: utf-8
# 
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.

import asyncio
from functools import partial
import yaml
from jira import JIRA

with open('config.yml', 'r') as config_file:
    config = yaml.safe_load(config_file)

async def main():
    loop = asyncio.get_event_loop()
    jira = JIRA(**config)
    project = await loop.run_in_executor(None, jira.project, 'MT')
    issue_list = [
    {
        'project': {'key': 'MT'},
        'summary': 'First issue of many',
        'description': 'Look into this one',
        'issuetype': {'name': 'Bug'},
    },
    {
        'project': {'key': 'MT'},
        'summary': 'Second issue',
        'description': 'Another one',
        'issuetype': {'name': 'Bug'},
    },
    {
        'project': {'key': 'MT'},
        'summary': 'Last issue',
        'description': 'Final issue of batch.',
        'issuetype': {'name': 'Bug'},
    }]
    issues = await loop.run_in_executor(None, partial(jira.create_issues, field_list=issue_list))
    issues = await loop.run_in_executor(None, jira.search_issues, 'project = MT')
    return issues

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    issues = loop.run_until_complete(main())
    print(issues)