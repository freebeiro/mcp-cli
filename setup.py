from setuptools import setup, find_packages

setup(
    name="mcp-cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "anyio",
        "pytest",
        "pytest-asyncio",
        "pydantic>=2.0.0",  # For data validation and JSON-RPC message handling
    ],
    extras_require={
        'dev': [
            'pytest-cov',  # For test coverage
        ]
    },
    python_requires='>=3.8',
    description="Model Context Protocol Command-Line Interface",
    author="Codeium",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
