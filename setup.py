try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'iPhone picture export/backup - not finished',
    'author': 'Jonathan Bowen',
    'url': 'github.com/jbowen102/iphone_pic_backup',
    'download_url': 'github.com/jbowen102/iphone_pic_backup.git',
    'author_email': 'jbowen@posteo.net',
    'version': '0.1',
    'install_requires': ['nose'],
    'packages': ['NAME'],
    'scripts': ['iphone_pic_bu.py'],
    'name': 'iphone_pic_backup'
}

setup(**config)
