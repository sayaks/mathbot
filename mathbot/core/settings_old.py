# A lot of the stuff in here is specific to MathBot,
# and is not generic.

import core.keystore
import itertools
import expiringdict


PMAP_COMMAND_ALLOW = {
	'enable': True,
	'disable': False,
	'original': None
}


CL_SELF = ['self']
CL_CHANNEL = ['channel', 'server']

SN_STANDARD = {
	'values': PMAP_COMMAND_ALLOW,
	'contexts': CL_CHANNEL,
	'default': True
}

SN_STANDARD_FALSE = {
	'values': PMAP_COMMAND_ALLOW,
	'contexts': CL_CHANNEL,
	'default': False
}


SETTINGS = {
	'c-tex': SN_STANDARD,
	'c-calc': SN_STANDARD,
	'c-wolf': SN_STANDARD,
	'f-calc-shortcut': SN_STANDARD,
	'f-wolf-filter': SN_STANDARD,
	'f-wolf-mention': SN_STANDARD,
	'f-inline-tex': SN_STANDARD_FALSE,
	'f-delete-tex': SN_STANDARD_FALSE,
	'p-tex-colour': { # This is now being used as a general 'theme' setting.
		'values': {
			'light': 'light',
			'dark': 'dark',
			'transparent': 'transparent',
			'original': None
		},
		'contexts': CL_SELF,
		'access': 'everyone',
		'default': 'light'
	},
	'p-tex-color':  {'redirect': 'p-tex-colour'},
	'f-tex-inline': {'redirect': 'f-inline-tex'},
	'f-tex-delete': {'redirect': 'f-delete-tex'}
}


def first_non_none(*args):
	for i in args:
		if i is not None:
			return i


async def channel_get_setting(message, parameter, default_override = None):
	return first_non_none(
		await get_setting_context(message, parameter, 'channel'),
		await get_setting_context(message, parameter, 'server'),
		default_override,
		SETTINGS[parameter].get('default')
	)


async def get_setting(message, parameter, default_override = None):
	details = SETTINGS.get(parameter)
	items = []
	for i in details['contexts']:
		items.append(await get_setting_context(message, parameter, i))
	return first_non_none(*items, default_override, details.get('default'))


def get_key(message, parameter, context):
	end = None
	if context == 'self':
		end = message.author.id
	elif context == 'channel':
		end = message.channel.id
		if message.channel.id == message.server.id:
			end += 'c'
	elif context == 'server':
		end = message.server.id
	return parameter + ':' + end


async def get_setting_context(message, parameter, context):
	if context in {'channel', 'server'} and message.channel.is_private:
		return None
	return await core.keystore.get(get_key(message, parameter, context))


def redirect(name):
	details = SETTINGS.get(name)
	if details:
		name = details.get('redirect', name)
	return name, SETTINGS.get(name)


PREFIX_CACHE = expiringdict.ExpiringDict(max_len = 10000, max_age_seconds = 120)


async def get_server_prefix(server_id):
	try:
		value = PREFIX_CACHE[server_id]
	except KeyError:
		value = await core.keystore.get('s-prefix:' + server_id) or '='
	PREFIX_CACHE[server_id] = value
	return value


async def get_channel_prefix(channel):
	if channel.is_private:
		return '='
	return await get_server_prefix(channel.server.id)


async def set_server_prefix(server_id, prefix):
	PREFIX_CACHE[server_id] = prefix
	await core.keystore.set('s-prefix:' + server_id, prefix)