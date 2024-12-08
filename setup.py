from setuptools import setup, find_packages

setup(
    name="mcp-cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "anyio",
        "pytest",
        "pytest-asyncio",
    ],
)
