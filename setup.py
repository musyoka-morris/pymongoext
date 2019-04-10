from os import path
from setuptools import setup, find_packages
from pymongoext import __version__

dirname = path.abspath(path.dirname(__file__))
with open(path.join(dirname, 'README.rst')) as f:
    long_description = f.read()

setup(
    name='pymongoext',
    version=__version__,
    packages=find_packages(),
    description='An ORM-like Pymongo extension that adds json schema validation, '
                'index management and intermediate data manipulators',
    url='https://github.com/musyoka-morris/pymongoext',
    license='MIT',
    author='Musyoka Morris',
    author_email='musyokamorris@gmail.com',
    classifiers=[
         'Development Status :: 3 - Alpha',
         'Intended Audience :: Developers',
         'Programming Language :: Python :: 3',
         'Programming Language :: Python :: 3.5',
         'Programming Language :: Python :: 3.6',
         'Programming Language :: Python :: 3.7'
    ],
    install_requires=open('requirements.txt').readlines(),
    python_requires='>=3',
    keywords='mongo mongodb database pymongo validation jsonschema schema indexes orm',
    include_package_data=True,
    long_description=long_description,
)
