from setuptools import setup, find_packages

setup(
    name='airena',
    version='0.0.1',
    description="AI contest in an RTS arena",
    url="http://github.com/dustinlacewell/airena",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        'straight.plugin',
    ],
)
