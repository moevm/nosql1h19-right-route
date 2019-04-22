import functools


def singleton(cls):
	"""
	Реализация паттерна одиночка
	:param cls:
	:return:
	"""
	instance=None

	@functools.wraps(cls)
	def inner(*args,**kwargs):
		nonlocal instance
		if instance is None:
			instance=cls(*args,**kwargs)
		return instance
	return inner


def projection(p1, p2, p3):
	y1, x1 = p1
	y2, x2 = p2
	y3, x3 = p3
	dx, dy = x2 - x1, y2 - y1
	det = dx * dx + dy * dy
	a = (dy * (y3 - y1) + dx * (x3 - x1)) / det
	return [y1 + a * dy, x1 + a * dx]

def bring_closer(info):
	import numpy as np
	y, x = projection(info['nodes'][0], info['nodes'][1], info['loc'])
	x1 = info['nodes'][0][1]
	x2 = info['nodes'][1][1]

	if x1 < x < x2 or x1 > x > x2:
		#print ('> жоно между')
		return [{'lat': info['loc'][0], 'lon': info['loc'][1]},
				{'lat': y, 'lon': x}]
	else:
		#print ('> оно не между')
		return [{'lat': info['loc'][0], 'lon': info['loc'][1]},
				{'lat': info['nodes'][0][0], 'lon': info['nodes'][0][1]}]
