#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# Univention Office 365 - print users subscriptions
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
from univention.config_registry import ConfigRegistry
from univention.office365.azure_handler import AzureHandler


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


def print_subscriptions():
	ucr = ConfigRegistry()
	ucr.load()
	ah = AzureHandler(ucr, "print_subscriptions")
	subscriptions = ah.list_subscriptions()["value"]

	# print all subscriptions
	data_fetchers = (
		itemgetter('skuPartNumber'),
		itemgetter('appliesTo'),
		itemgetter('capabilityStatus'),
		lambda x: x["prepaidUnits"]["enabled"] + x["prepaidUnits"]["suspended"] + x["prepaidUnits"]["warning"] - x["consumedUnits"],
		itemgetter('consumedUnits'),
		lambda x: '{enabled}/{suspended}/{warning}'.format(**x['prepaidUnits'])
	)
	header_parts = ('Subscription', 'Applies to', 'Status', 'Consumed',  'Remaining', 'Prepaid (*)')
	line = '{: <%d} | {: <%d} | {: <%d} | {: >%d} | {: >%d} | {: >%d}'
	epilog = '(*) enabled/suspended/warning\n'
	header = ' | '.join(header_parts)
	print(('{: ^%d}' % len(header)).format('Subscriptions'))
	print(('{: ^%d}' % len(header)).format('=' * (len('Subscriptions') + 8)))
	print_table(subscriptions, data_fetchers, header_parts, line, epilog)

	# list plans of all subscriptions
	data_fetchers = (
		itemgetter('servicePlanName'),
		itemgetter('appliesTo'),
		itemgetter('provisioningStatus'),
		lambda x: 'x' if x['servicePlanName'] in ah.service_plan_names else ''
	)
	header_parts = ('Service plan', 'Applies to', 'Status', 'in UCRV (*)')
	line = '{: <%d} | {: <%d} | {: <%d} | {: <%d}'
	epilog = '(*) office365/subscriptions/service_plan_names\n'
	header = ' | '.join(header_parts)
	column_lengths = tuple(0 for x in header_parts)
	# make columns homogeneous for all subscriptions
	for subscription in subscriptions:
		plan_column_length = calc_column_lengths(subscription["servicePlans"], data_fetchers, header_parts)
		column_lengths = tuple(max(column_lengths[x], plan_column_length[x]) for x in range(len(column_lengths)))
	# print each subscription
	for subscription in subscriptions:
		print(('{: ^%d}' % len(header)).format(subscription['skuPartNumber']))
		print(('{: ^%d}' % len(header)).format('=' * (len(subscription['skuPartNumber']) + 8)))
		print_table(subscription["servicePlans"], data_fetchers, header_parts, line, epilog, column_lengths)


if __name__ == '__main__':
	print_subscriptions()
