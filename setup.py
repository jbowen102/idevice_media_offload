try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'iPhone picture export/backup - not finished',
    'author': 'Jonathan Bowen',
    'url': 'URL to get it at.'
    'download_url': 'Where to download it.',
    'author_email': 'jjbowen19@gmail.com',
    'version': '0.1',
    'install_requires': ['nose'],
    'packages': ['NAME'],
    'scripts': ['iphone_pic_bu.py'],
    'name': 'iphone_pic_backup'
}

setup(**config)
