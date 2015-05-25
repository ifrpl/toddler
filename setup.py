__author__ = 'michal'

from setuptools import setup, find_packages

requirements = [
    "PyYAML==3.11",
    "Pygments==2.0.2",
    "addict==0.2.7",
    "aiohttp==0.14.4",
    "beautifulsoup4==4.3.2",
    "blinker==1.3",
    "colorama==0.3.3",
    "colored-traceback==0.2.1",
    "coverage==3.7.1",
    "lxml==3.4.2",
    "mongoengine==0.9.0",
    "mongomock==2.0.0",
    "publicsuffix==1.0.5",
    "pymongo==2.8",
    "python-dateutil==2.4.0",
    "python3-pika==0.9.14",
    "requests==2.5.1",
    "sentinels==0.0.6",
    "six==1.9.0",
    "ujson==1.33",
    "url==0.1.2",
]

setup(
    name="toddler",
    version="0.0.1",
    author="IF Research Polska Sp. z o. o.",
    description="Awesome crawler and indexer like no other",
    url="https://bitbucket.org/michalmazurek/toddler/",
    include_package_data=True,
    packages=find_packages(exclude=['tests']),
    scripts=['bin/toddler-run', 'bin/toddler-tools'],
    install_requires=requirements
)