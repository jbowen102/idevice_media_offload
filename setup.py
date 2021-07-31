try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'iPhone and iPad picture export/backup, organization, and categorization',
    'author': 'Jonathan Bowen',
    'url': 'github.com/jbowen102/idevice_media_offload',
    'download_url': 'github.com/jbowen102/idevice_media_offload.git',
    'author_email': 'ew15dro6k216@opayq.net',
    'version': '0.1',
    'install_requires': ['exiftool', 'PIL', 'mediadapt'],
    'packages': [''],
    'scripts': [''],
    'name': 'idevice_media_offload'
}

setup(**config)
