import aioredis
import os
import re
import core.keystore
import core.help
import core.settings


SETTING_COMMAND_ARG_ERROR = """
Invalid number of arguments.
Usage:
	`=set context setting value`
Type `=help settings` for more information.\
"""


SETTING_COMMAND_PRIVATE_ERROR = """
The `settings` command cannot be used in a private channel.
Type `=help settings` for more information.\
"""


SETTING_COMMAND_PERMS_ERROR = """
You need to be an admin on this server to use this command here.
"""


SETTING_COMMAND_RESPONSE = """\
The following setting has been applied:
```
Setting: {setting}
Value: {value}
Context: {context}
```
"""


core.help.load_from_file('./help/settings.md')
core.help.load_from_file('./help/theme.md')
core.help.load_from_file('./help/prefix.md')


INVALID_SETTING_MESSAGE = '''\
Invalid setting "{setting}".

The following settings exist:
{valid_settings}

See `=help settings` for more details.
'''


INVALID_CONTEXT_MESSAGE = '''\
Invalid context parameter "{context}".

Setting "{setting}" supports the following contexts:
{valid_contexts}

See `=help settings` for more details.
'''


INVALID_VALUE_MESSAGE = '''\
Invalid value parameter "{value}".

Setting "{setting}" supports the following values:
{valid_values}

See `=help settings` for more details.
'''


CHECKSETTING_TEMPLATE = '''\
Setting "{}" has the following values:
```
Channel: {}
Server:  {}
Default: {}
```
'''


def format_bullet_points(l):
	return '\n'.join(map(lambda c: ' - ' + c, l))


GLOBAL_ELEVATION = {
	'133804143721578505' # DXsmiley
}


def is_admin_message(m, prevent_global_elevation = False):
	if m.channel.is_private:
		return True
	if m.author.id in GLOBAL_ELEVATION and not prevent_global_elevation:
		return True
	perms = m.channel.permissions_for(m.author)
	return perms.administrator or perms.manage_server


class ProblemReporter:

	def __init__(self, module, channel):
		self.problems = []
		self.module = module
		self.channel = channel

	async def __aenter__(self):
		return self._report

	async def __aexit__(self, type, value, traceback):
		if self.problems:
			msg = '\n'.join(self.problems)
			await self.module.send_message(self.channel, msg)
			raise WasProblems

	def _report(self, text):
		self.problems.append(text)


class WasProblems(Exception):
	pass


class SettingsModule(core.module.Module):

	reduce_value = {
		'enable': 1,
		'disable': 0,
		'reset': None,
		'original': None,
		'e': 1,
		'd': 0,
		'r': None,
		'o': None
	}.get

	expand_value = {
		None: '--------',
		1: 'enabled',
		0: 'disabled',
		True: 'enabled',
		False: 'disabled'
	}.get

	@core.handles.command('settings setting set', 'string string string')
	async def command_set(self, message, context, setting, value):
		try:
			async with ProblemReporter(self, message.channel) as problem:
				if message.channel.is_private:
					problem('This command cannot be used in private channels.')
			async with ProblemReporter(self, message.channel) as problem:
				setting_details = core.settings.details(setting)
				if setting_details is None:
					problem('`{}` is not a valid setting. See `=help settings` for a list of valid settings.'.format(setting))
				if context not in ['server', 'channel', 's', 'c']:
					problem('`{}` is not a valid context. Options are: `server` or `channel`'.format(context))
				if value not in ['enable', 'disable', 'original', 'e', 'd', 'o', 'reset', 'r']:
					problem('`{}` is not a valid value. Options are `enable`, `disable`, `reset`.'.format(value))
		except WasProblems:
			pass
		else:
			ctx = {'s': message.server, 'c': message.channel}[context[0]]
			val = SettingsModule.reduce_value(value)
			await core.settings.set(setting, ctx, val)
			await self.send_message(message.channel, 'Setting applied.', blame = message.author)

	@core.handles.command('theme', 'string')
	async def command_theme(self, message, theme):
		theme = theme.lower()
		if theme not in ['light', 'dark']:
			m = '`{theme}` is not a valid theme. Valid options are `light` and `dark`.'
		else:

			key = 'p-tex-colour:' + message.author.id
			await core.keystore.set(key, theme)
			m = 'Your theme has been set to `{theme}`.'
		await self.send_message(message.channel, m.format(theme = theme), blame = message.author)

	@core.handles.command('checksetting', 'string')
	async def command_checksetting(self, message, setting):
		if message.channel.is_private:
			await self.send_message(message.channel, 'This command cannot be used in private channels.', blame = message.author)
		elif core.settings.details(setting) is None:
			await self.send_message(message.channel, '`{}` is not a valid setting. See `=help settings` for a list of valid settings.'.format(setting), blame = message.author)
		else:
			value_server  = await core.settings.get_single(setting, message.server)
			value_channel = await core.settings.get_single(setting, message.channel)
			print('Details for', setting)
			print('Server: ', value_server)
			print('Channel:', value_channel)
			default = core.settings.details(setting).get('default')
			m = CHECKSETTING_TEMPLATE.format(
				setting,
				SettingsModule.expand_value(value_channel),
				SettingsModule.expand_value(value_server),
				SettingsModule.expand_value(default)
			)
			await self.send_message(message.channel, m, blame = message.author)


	@core.handles.command('checkallsettings', '')
	async def command_check_all_settings(self, message):
		if message.channel.is_private:
			await self.send_message(message.channel, 'This command cannot be used in private channels.', blame = message.author)
		else:
			lines = [' Setting          | Channel  | Server   | Default',
					 '------------------+----------+----------+----------'
			]
			for setting, s_details in core.settings.SETTINGS.items():
				if 'redirect' not in s_details:
					value_channel = await core.settings.get_single(setting, message.channel)
					value_server  = await core.settings.get_single(setting, message.server)
					lines.append(' {: <16} | {: <8} | {: <8} | {: <8}'.format(
						setting,
						SettingsModule.expand_value(value_channel),
						SettingsModule.expand_value(value_server),
						SettingsModule.expand_value(s_details['default'])
					))
			m = '```\n{}\n```'.format('\n'.join(lines))
			await self.send_message(message.channel, m, blame = message.author)


	@core.handles.command('prefix', '*')
	async def command_prefix(self, message, arg):
		print('=prefix command')
		if message.channel.is_private:
			await self.send_message(message.channel, 'This command does not apply to private channels', blame = message.author)
		elif arg == '':
			prefix = await core.settings.get_server_prefix(message.server)
			if prefix is None or prefix == '=':
				m = 'The prefix for this server is `=`, which is the default.'
			else:
				m = 'The prefix for this server is `{}`, which has been customised.'.format(prefix)
			await self.send_message(message.channel, m, blame = message.author)
		elif not is_admin_message(message):
			await self.send_message(message.channel, 'You must be an admin on this server to change the prefix', blame = message.author)
		else:
			prefix = arg.strip().replace('`', '')
			await core.settings.set_server_prefix(message.server, prefix)
			await self.send_message(message.channel, 'Bot prefix for this server has been changed to `{}`.'.format(prefix), blame = message.author)
