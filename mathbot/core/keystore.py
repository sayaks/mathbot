# A simple key-value store that can either be hooked
# up to redis (for production) or just read and write
# a file on disk.


import re
import asyncio
import collections
import json
import aioredis
import time


class Interface:

	async def get(self, key):
		raise NotImplementedError

	async def set(self, key, value):
		raise NotImplementedError

	async def expire(self, key, time):
		raise NotImplementedError


class Redis(Interface):

	def __init__(self, url, number = 0):
		self.url = url
		self.db_number = number
		self.started = False
		self.connection = None
		self.startup_lock = asyncio.Lock()

	async def ensure_started(self):
		with await self.startup_lock:
			if not self.started:
				self.started = True
				user, password, host, port = re.split(r':|@', self.url[8:])
				if password == '':
					password = None
				self.connection = await aioredis.create_reconnecting_redis(
					(host, int(port)),
					password = password,
					db = self.db_number
				)
				print('Connected to redis server!')

	def decipher(self, value):
		if value is None:
			return None
		string = value.decode('utf-8')
		try:
			integer = int(string)
			return integer
		except ValueError:
			pass
		return string

	async def get(self, key):
		await self.ensure_started()
		return self.decipher(await self.connection.get(key))

	async def set(self, key, value):
		await self.ensure_started()
		return await self.connection.set(key, value)

	async def delete(self, key):
		await self.ensure_started()
		return await self.connection.delete(key)

	async def expire(self, key, time):
		await self.ensure_started()
		return await self.connection.expire(key, time)

	async def lpush(self, key, value):
		await self.ensure_started()
		return await self.connection.lpush(key, value)

	async def rpop(self, key):
		await self.ensure_started()
		return self.decipher(await self.connection.rpop(key))


class Disk(Interface):

	def __init__(self, filename = None):
		self.filename = filename
		self.data = collections.defaultdict(
			lambda : {
				'value': None,
				'expires': None
			}
		)
		self.load()

	def load(self):
		if self.filename:
			try:
				with open(self.filename) as f:
					stored = json.load(f)
					self.data.update(stored)
					for key, value in self.data.items():
						if isinstance(value['value'], list):
							value['value'] = collections.deque(value['value'])
			except FileNotFoundError:
				pass

	def save(self):
		if self.filename:
			with open(self.filename, 'w') as f:
				blob = {
					key : {
						'value': list(value['value']) if isinstance(value['value'], collections.deque) else value['value'],
						'expires': value['expires']
					}
					for key, value in self.data.items()
				}
				json.dump(blob, f, indent = 4)

	def is_expired(self, key):
		if self.data[key]['expires'] is not None:
			if self.data[key]['expires'] < time.time():
				return True
		return False

	async def get(self, key):
		# if the key is expires, there is no value
		if self.is_expired(key):
			self.data[key]['value'] = None
		return self.data[key]['value']

	async def set(self, key, value):
		# If the key is expired, the new key has no expiery
		if self.is_expired(key):
			self.data[key]['value'] = None
		self.data[key] = {
			'value': value,
			'expires': None
		}
		self.save()

	async def delete(self, key):
		if key in self.data:
			del self.data[key]

	async def expire(self, key, seconds):
		self.data[key]['expires'] = time.time() + seconds
		self.save()

	async def lpush(self, key, value):
		if not isinstance(self.data[key]['value'], collections.deque):
			await self.set(key, collections.deque())
		self.data[key]['value'].appendleft(value)
		self.save()

	async def rpop(self, key):
		if not isinstance(self.data[key]['value'], collections.deque):
			await self.set(key, collections.deque())
		if len(self.data[key]['value']) == 0:
			return None
		return self.data[key]['value'].pop()


KEY_DELIMITER = ':'
SETUP = False
INTERFACE = None


def setup_redis(url, number = 0):
	global INTERFACE
	INTERFACE = Redis(url, number)
	SETUP = True


def setup_disk(filename):
	global INTERFACE
	INTERFACE = Disk(filename)
	SETUP = True


def reduce_key(keys):
	assert(len(keys) >= 1)
	# for i in keys:
	# 	assert(KEY_DELIMITER not in i)
	return KEY_DELIMITER.join(keys)


def reduce_key_val(keys):
	assert(len(keys) >= 2)
	return KEY_DELIMITER.join(keys[:-1]), keys[-1]


async def get(*keys):
	key = reduce_key(keys)
	return await INTERFACE.get(key)


# It's a bit strange how the end of this is the value
async def set(*args, expire = None):
	assert(len(args) >= 2)
	key, value = reduce_key_val(args)
	await INTERFACE.set(key, value)
	if expire is not None:
		await INTERFACE.expire(key, expire)


async def get_json(*keys):
	data = await get(*keys)
	return None if data is None else json.loads(data)


async def set_json(*args, expire = None):
	assert(len(args) >= 2)
	key, value = reduce_key_val(args)
	await INTERFACE.set(key, json.dumps(value))
	if expire is not None:
		await INTERFACE.expire(key, expire)

async def lpush(*args):
	key, value = reduce_key_val(args)
	await INTERFACE.lpush(key, value)

async def rpop(*keys):
	key = reduce_key(keys)
	return await INTERFACE.rpop(key)

async def delete(*args):
	assert(len(args) >= 1)
	key = reduce_key(args)
	await INTERFACE.delete(key)


async def expire(*args):
	assert(len(args) >= 2)
	args = list(args)
	time = args.pop()
	key = reduce_key(args)
	await INTERFACE.expire(key, time)
