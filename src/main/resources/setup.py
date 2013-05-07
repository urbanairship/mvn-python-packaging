from setuptools import setup, find_packages

requirements = [l.strip() for l in open('requirements.txt').readlines()]

setup(
    name='${python_package}',
    url='${source_url}',
    version='${python_version}',
    author='${author}',
    author_email='${author_email}',
    description='${description}',
    packages=find_packages(),
    install_requires=requirements,
    include_package_data=True,
)
