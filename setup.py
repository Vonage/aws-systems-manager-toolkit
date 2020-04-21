import io
import os
from setuptools import find_namespace_packages, setup
import toolkit


# Package meta-data.
NAME = 'aws-systems-manager-toolkit'
DESCRIPTION = 'Wrapper tools for AWS Systems Manager'
URL = 'https://github.com/vonage/aws-systems-manager-toolkit'
EMAIL = 'sre@vonage.com'
AUTHOR = 'Vonage SRE'
REQUIRES_PYTHON = '>=3.6.0'
VERSION = toolkit.__version__

# The directory containing this file
here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        README = '\n' + f.read()
except FileNotFoundError:
    README = DESCRIPTION


# This call to setup() does all the work
setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=README,
    long_description_content_type="text/markdown",
    url=URL,
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    include_package_data=True,
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
    packages=find_namespace_packages(exclude=("docs",)),
    install_requires=["boto3", "botocore"],
    entry_points={
        "console_scripts": [
            "ssm-connect=toolkit.ssm_connect:main",
            "ssm-list=toolkit.ssm_list:main",
            "ssm-port-forward=toolkit.ssm_port_forward:main",
            "ssm-run=toolkit.ssm_run:main",
            "ssm-ssh=toolkit.ssm_ssh:main",
        ]
    },
)