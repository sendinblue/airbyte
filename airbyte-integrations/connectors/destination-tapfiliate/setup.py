#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from setuptools import find_packages, setup

MAIN_REQUIREMENTS = [
    "airbyte-cdk","requests"
]

TEST_REQUIREMENTS = ["pytest"]

setup(
    name="destination_tapfiliate",
    description="Destination implementation for Tapfiliate.",
    author="Airbyte",
    author_email="kim.plavonil@brevo.com",
    packages=find_packages(),
    install_requires=MAIN_REQUIREMENTS,
    package_data={"": ["*.json"]},
    extras_require={
        "tests": TEST_REQUIREMENTS,
    },
)
