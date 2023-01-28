httpim - HTTP-based imaeg gallery server with thumbnails & caching
------------------------------------------------------------------

# Why?

Have you ever hosted a local server with `python -m http.server`, but it lacks the ability to show image thumbnails so you could not find what you needed fast?

Or maybe you're playing with stable diffusion model and want to share `/outputs` folder with your friends?

If the answer is yes, this small tool is for you.

# Features

HTTPIM Implements:
* Server-side page rendering
* Showing previews for image files (.png/.gif/.jpeg/.bmp/.tiff) as sompressed jpeg with desired size (64x64, 128x128, etc.)
* Caching thumbnails inside `__httim_cache__` folder that can be easily deleted with `python httpim.py -r` when you're done
* Showing screen-adaptive grid of folders + images + go up a level

# Install as module

**WARNING: this version does not have setup bundle, thus can cause problems on upgrade**

Install with `pip install httpim`

Run with `python -m httpim`

# Usage

```
usage: httpim.py [-h] [-l LISTEN] [-p PORT] [-d PATH] [-t THUMB] [--license] [-r]

httpim

optional arguments:
  -h, --help            show this help message and exit
  -l LISTEN, --listen LISTEN
                        Server IP
  -p PORT, --port PORT  Server port
  -d PATH, --path PATH  Server port
  -t THUMB, --thumb THUMB
                        Thumbnail size
  --license             License
  -r, --clear-cache     Clear cache
```

# LICENSE
```
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
```

# TODO:
* pypi package
* external path-safety check audition
