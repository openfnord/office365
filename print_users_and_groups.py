#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# Univention Office 365 - print users and groups
#
# Copyright 2016 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

from operator import itemgetter
from univention.office365.listener import Office365Listener
from univention.office365.azure_handler import ResourceNotFoundError


def calc_column_lengths(data, data_fetchers, header_parts):
	rows = [tuple(len(x) for x in header_parts)]
	for part in data:
		rows.append(tuple(max(len(x) for x in str(df(part)).split('\n')) for df in data_fetchers))
	return tuple(max(r[i] for r in rows) for i in range(len(header_parts)))


def print_table(data, data_fetchers, header_parts, line, epilog, column_lengths=None):
	if not column_lengths:
		column_lengths = calc_column_lengths(data, data_fetchers, header_parts)
	header = (line.replace('<%', '^%') % column_lengths).format(*header_parts)
	print(header)
	print('-' * len(header))
	line %= column_lengths
	for part in data:
		print(line.format(*tuple(df(part) for df in data_fetchers)))
	print('-' * len(header))
	print(epilog)


def print_users_and_groups():
	ol = Office365Listener({}, "print users and groups", {}, {}, "dn")
	users = ol.ah.list_users()
	groups = ol.ah.list_groups()

	# print users
	plans = set(
		plan['service'] for user in users['value']
		for plan in user['assignedPlans']
		if plan['capabilityStatus'] == 'Enabled'
	)
	plan_to_num = dict((plan, num) for num, plan in enumerate(sorted(plans), 1))
	data_fetchers = (
		lambda x: '(DEL) {}'.format(x['displayName'][26:]) if x['displayName'].startswith("ZZZ_deleted_") else x[
			'displayName'],
		lambda x: 'x' if x['accountEnabled'] else '',
		itemgetter('userPrincipalName'),
		lambda x: ', '.join(
			map(str, sorted(set(
				plan_to_num[x['service']]
				for x in x['assignedPlans']
				if x['capabilityStatus'] == 'Enabled')
			)))
	)
	header_parts = ('User', 'Enabled', 'User Principal Name', 'Enabled plans (*)')
	line = '{: <%d} | {: <%d} | {: <%d} | {: <%d}'
	epilog = '(*) '
	plan_names = sorted(plan_to_num.keys())
	for i in range(0, len(plan_names), 4):
		epilog += '{}{}\n'.format(
			'    ' if i > 0 else '',
			', '.join(['{}: {}'.format(plan_to_num[plan], plan) for plan in plan_names[i:i + 4]]))
	print_table(users["value"], data_fetchers, header_parts, line, epilog)

	# print groups
	member_ids = dict()
	for group in groups["value"]:
		member_urls = ol.ah.get_groups_direct_members(group["objectId"])["value"]
		member_ids[group["displayName"]] = ol.ah.directory_object_urls_to_object_ids(member_urls)

	group_members = list()
	for name, member_ids in member_ids.items():
		membernames = list()
		for member_id in member_ids:
			try:
				member = ol.ah.list_users(objectid=member_id)
				membername = member["userPrincipalName"]
				if membername.startswith("ZZZ_deleted_"):
					membername = "(DEL) {}".format(membername[26:])
			except ResourceNotFoundError:
				member = ol.ah.list_groups(objectid=member_id)
				membername = member["displayName"]
				if membername.startswith("ZZZ_deleted_"):
					membername = "(DEL, group) {}".format(membername[26:])
				else:
					membername = '(group) {}'.format(membername)
			membernames.append(membername)
		group_members.append((name, membernames))

	header_parts = ('Group', '#', 'Members')
	line = '{: <%d} | {: <%d} | {: <%d}'
	data_fetchers = (
		itemgetter(0),
		lambda x: len(x[1]),
		lambda x: '\n'.join(x[1])
	)
	column_lengths = calc_column_lengths(group_members, data_fetchers, header_parts)
	continuation_line = line % column_lengths

	def lis2str(li):
		if not li:
			return ''
		elif len(li) == 1:
			return li[0]
		else:
			li2 = [li[0]]
			li2.extend(continuation_line.format('', '', x) for x in li[1:])
			return '\n'.join(li2)

	data_fetchers = (
		itemgetter(0),
		lambda x: len(x[1]),
		lambda x: lis2str(x[1])
	)
	epilog = ''
	print_table(group_members, data_fetchers, header_parts, line, epilog, column_lengths)


if __name__ == '__main__':
	print_users_and_groups()
