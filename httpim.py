COPYRIGHT = """
HTTP server for image browsing
Copyright (C) 2023  bitrate16

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import sys
import time
import shutil
import sqlite3
import argparse
import mimetypes

import email.utils
import datetime

from PIL import Image
from urllib.parse import urlparse, unquote
from http.server import HTTPServer, BaseHTTPRequestHandler

def format_dir_html(name: str, relpath: str):
	return f"""<a class="dir" href="{ relpath }">
	<p class="type">DIR</p>
	<p class="name">{ name }</p>
</a>"""

def format_up_dir_html(relpath: str):
	parent = relpath.rsplit('/', 1)[0]
	if parent == '':
		parent = '/'
	return f"""<a class="dir" href="{ parent }">
	<p class="type">^ UP</p>
</a>"""

def format_thumb_html(name: str, relpath: str):
	if relpath.startswith('/__httpim_cache__'):
		return f"""<a class="thumb" href="{ relpath }">
	<img src="{ relpath }" loading="lazy" onerror="hot_reload(this);">
	<p class="name">{ name }</p>
</a>"""
	else:
		return f"""<a class="thumb" href="{ relpath }">
	<img src="/__httpim_cache__{ relpath }" loading="lazy" onerror="hot_reload(this);">
	<p class="name">{ name }</p>
</a>"""

def format_file_html(name: str, relpath: str):
	ext = name.rsplit('.', 1)[-1]
	return f"""<a class="file" href="{ relpath }">
	<p class="type">{ ext }</p>
	<p class="name">{ name }</p>
</a>"""

def iter_dir_page_bytes(realpath: str, relpath: str):
	"""Return page as bytes iterator for given folder path & relpath. Folder must exist"""

	try:
		files = os.listdir(realpath)
	except:
		files = []

	# Write first part
	yield f"""<html>
<title>Directory listing for { relpath }</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<script type="text/javascript">
	function hot_reload(element) {{
		setTimeout(function() {{
			element.src = element.src;
		}}, 500);
	}}
</script>
<style>
	html, body {{
		padding: 0;
		margin: 0;
	}}
	* {{
		box-sizing: border-box;
	}}
	body {{
		display: flex;
		flex-direction: row;
		justify-content: center;
		flex-wrap: wrap;
		gap: 1rem;
		padding: 1rem;
	}}
	a {{
		text-decoration: none;
		width: min(20vmin, 10rem);
		height: min(20vmin, 10rem);
		position: relative;
	}}
	a:hover {{
		opacity: 75%;
	}}
	a.thumb > img {{
		width: 100%;
		height: 100%;
	}}
	a.thumb > p.name {{
		background-color: #fff4;
	}}
	a > p.name {{
		width: 100%;
		height: auto;
		margin: 0;
		position: absolute;
		padding: 0 min(0.5vmin, 0.25rem) min(0.5vmin, 0.25rem) min(0.5vmin, 0.25rem);
		bottom: 0;
		left: 0;
		overflow-wrap: break-word;
		font-family: 'Courier New', Courier, monospace;
		color: black;
		font-size: min(1.5vmin, 0.75rem);
		text-align: center;
	}}
	p.type {{
		width: 100%;
		margin: 0;
		position: absolute;
		padding: min(1vmin, 0.5rem);
		top: 0;
		left: 0;
		overflow-wrap: break-word;
		font-weight: bold;
		font-family: 'Courier New', Courier, monospace;
		color: black;
		font-size: min(4vmin, 2rem);
		text-align: center;
		z-index: 50;
	}}
	a.dir {{
		outline-offset: max(-0.5vmin, -0.25rem);
		outline: min(0.5vmin, 0.25rem) dashed black;
	}}
	a.dir:hover {{
		outline: min(0.5vmin, 0.25rem) dashed #000a;
	}}
	a.file {{
		outline-offset: max(-0.5vmin, -0.25rem);
		outline: min(0.5vmin, 0.25rem) dotted black;
		background-color: #ddd;
	}}
	a.file:hover {{
		outline: min(0.5vmin, 0.25rem) dotted #000a;
	}}
</style>
<body>""".encode("utf8")

	# Write up step dir
	if relpath != '/':
		yield format_up_dir_html(relpath).encode('utf8')

	# Process dirs & files
	for file in files:
		file_relpath = url_pathjoin(relpath, file)
		file_realpath = os.path.join(realpath, file)

		# Send file
		if os.path.isfile(file_realpath):
			if file_can_thumb(file):
				yield format_thumb_html(file, file_relpath).encode('utf8')
			else:
				yield format_file_html(file, file_relpath).encode('utf8')

		# Send dir
		elif os.path.isdir(file_realpath):
			yield format_dir_html(file, file_relpath).encode('utf8')

	yield """	</body>
</html>""".encode('utf8')

def file_can_thumb(path: str):
	"""Checks if given file can have an image thumbnail"""
	return path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))

def url_pathjoin(a: str, b: str):
	if a.endswith('/'):
		a = a[:-1]
	if b.startswith('/'):
		b = b[1:]
	c = a + '/' + b
	if not c.startswith('/'):
		c = '/' + c
	return c

def check_url_path_safety(url_path: str) -> bool:
	"""
	Checks if URL path is safe for path concatenation.

	Returns Fals if URL path contains canonical rebase and/or parent/home/curdir
	placements, excessive slashes at the beginning or leading/trailing spaces
	(^ - start, $  -end of string):
	* `foo/../bar` or `^../foo` or `foo/..$`
	* `foo/./bar` or `^./foo` or `foo/.$`
	* `foo/~/bar` or `^~/foo` or `foo/~$`
	* `^//foo`
	* `^ foo` or `foo $`

	@from: pegasko.art/application/path.py
	"""

	# No:
	# ~/
	# ./
	# ../
	# //
	# " "
	if url_path.startswith((
		'~/',  # Home jump
		'./',  # Workdir jump
		'../', # Up jump
		'//',  # Double slash
		' ',   # Leading space
	)):
		return False

	# No:
	# /~
	# /.
	# /..
	# " "
	if url_path.endswith((
		'/~',  # Home postjump
		'/.',  # Workdir postjump
		'/..', # Up postjump
		' ',   # Trailing space
	)):
		return False

	# No:
	# /./
	# /../
	# /~/
	if '/./' in url_path or '/../' in url_path or '/~/' in url_path:
		return False

	return True

def url_path_strip(url_path: str) -> str:
	"""
	Strip URL path string to remove leading/trailing spaced, trailing slash and
	duplicating leading slashes:

	Converts:
	* `" foo/bar " -> "foo/bar"`
	* `"///foo/bar///" -> "/foo/bar"`
	* `" / /  /foo/bar/ /   / " -> "/foo/bar"`

	Returns url as `foo/bar/baz` without leading slash

	@from: pegasko.art/application/path.py
	"""

	cut = 0
	while (len(url_path) - cut) != 0 and (url_path[cut] == ' ' or url_path[cut] == '/'):
		cut += 1
	url_path = url_path[cut:]

	cut = 0
	while (len(url_path) - cut) != 0 and (url_path[len(url_path)-cut-1] == ' ' or url_path[len(url_path)-cut-1] == '/'):
		cut += 1
	url_path = url_path[:len(url_path)-cut]
	return url_path

class HTTPIM(BaseHTTPRequestHandler):
	def setup(self):
		BaseHTTPRequestHandler.setup(self)
		self.request.settimeout(60)

	def _do_404(self):
		self.send_response(404)
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		self.wfile.write('Not Found'.encode('utf8'))

	def _do_file(self, path):
		ctype = mimetypes.guess_type(path)[0]

		try:
			f = open(path, 'rb')
		except OSError:
			return self._do_404()

		try:
			# Do headers
			stat = os.fstat(f.fileno())

			if ('If-Modified-Since' in self.headers and 'If-None-Match' not in self.headers):
				try:
					ts = email.utils.parsedate_to_datetime(self.headers['If-Modified-Since'])

					if ts.tzinfo is None:
						ts = ts.tzinfo.replace(tzinfo=datetime.timezone.utc)

					if ts.tzinfo is datetime.timezone.utc:
						last_modified = datetime.datetime.fromtimestamp(stat.st_mtime, datetime.timezone.utc)
						last_modified.replace(microsecond=0)

						if last_modified <= ts:
							self.send_response(304)
							self.end_headers()
							f.close()
							return
				except:
					pass

			self.send_response(200)
			self.send_header("Content-type", ctype)
			self.send_header("Content-Length", str(stat[6]))
			self.send_header("Last-Modified", email.utils.formatdate(stat.st_mtime or time.time(), usegmt=True))
			self.end_headers()

			# Do file contents
			try:
				shutil.copyfileobj(f, self.wfile)
			finally:
				f.close()
		except:
			import traceback
			traceback.print_exc()
			f.close()
			return self._do_404()

	def _do_dir(self, realpath: str, relpath: str):
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()

		for frag in iter_dir_page_bytes(realpath, relpath):
			self.wfile.write(frag)
			self.wfile.flush()

	def do_GET(self):
		"""Handle complete GET"""
		parsed = urlparse(self.path)
		path: str = unquote(parsed.path.strip())
		path = '/' + url_path_strip(path)

		# Prevent go up/down/elsewhere via canonical path injection
		if not check_url_path_safety(path):
			return self._do_404()

		# Cached file response
		if path.startswith('/__httpim_cache__/'):
			cachepath = os.path.join(args.cachepath, path[len('/__httpim_cache__/'):])
			realpath = os.path.join(args.path, path[len('/__httpim_cache__/'):])
		else:
			cachepath = None
			realpath = os.path.join(args.path, path[1:]) # Strip /

		# Check if directory
		if os.path.isdir(realpath):
			return self._do_dir(realpath, path)

		# Direct return from cache
		if cachepath is not None:
			# All thumbs are jpeg
			cachepath, _ = os.path.splitext(cachepath)
			cachepath = f'{ cachepath }.jpg'

			if os.path.exists(cachepath):
				return self._do_file(cachepath)

			# Check if file is allowed to have thumbnail
			if not file_can_thumb(realpath):
				return self._do_404()

			# Try to build thumbnail
			try:
				os.makedirs(os.path.dirname(cachepath), exist_ok=True)
				img = Image.open(realpath)
				img.thumbnail((args.thumb, args.thumb))
				img.save(cachepath, 'JPEG', quality=95)
			except:
				import traceback
				traceback.print_exc()
				return self._do_404()

			# Send thumbnail
			return self._do_file(cachepath)

		# Return normal file
		else:
			# As normal file
			if os.path.exists(realpath):
				return self._do_file(realpath)

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='httpim')
	parser.add_argument(
		'-l',
		'--listen',
		default='0.0.0.0',
		help='Server IP',
	)
	parser.add_argument(
		'-p',
		'--port',
		type=int,
		default=8000,
		help='Server port',
	)
	parser.add_argument(
		'-d',
		'--path',
		type=str,
		default='.',
		help='Server port',
	)
	parser.add_argument(
		'-t',
		'--thumb',
		type=int,
		default=256,
		help='Thumbnail size',
	)
	parser.add_argument(
		'--license',
		action='store_true',
		help='License',
	)
	parser.add_argument(
		'-r',
		'--clear-cache',
		dest='clear_cache',
		action='store_true',
		help='Clear cache',
	)

	args = parser.parse_args()

	if args.license:
		print(COPYRIGHT)
		exit(0)

	# Resolve abspath for root & cache
	args.path = os.path.abspath(args.path)
	args.cachepath = os.path.join(args.path, '__httpim_cache__')

	if args.clear_cache:
		try:
			shutil.rmtree(args.cachepath, ignore_errors=True)
		except:
			import traceback
			traceback.print_exc()
		exit(0)

	os.makedirs(args.cachepath, exist_ok=True)

	print(f'Starting server on { args.listen }:{ args.port }')
	try:
		httpd = HTTPServer((args.listen, args.port), HTTPIM)
		httpd.serve_forever()
	except KeyboardInterrupt:
		print('Keyboard interrupt received, exiting.')
