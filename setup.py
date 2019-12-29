"""
See: https://setuptools.readthedocs.io/en/latest/setuptools.html
"""

from distutils.core import setup
import setuptools
import glob

name='cxgame'
version='1.0'
release='1.0.0'

setup(
    name=name,
    version=release,
    author='Matth Ingersoll',
    author_email='matth@mtingers.com',
    packages=[name,],
    license='Other/Proprietary License',
    long_description='Cryptocurrency Exchange Game',
    url='https://github.com/mtingers/cxgame',
    entry_points={
        'console_scripts': ['cxgame=cxgame.server:main',],
    },
    install_requires=open('requirements.txt').read().strip().split('\n'),
    scripts=glob.glob('bin/*'),
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
