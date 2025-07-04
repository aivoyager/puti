from setuptools import setup, find_packages
import os

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_PROJECT_ROOT, "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()


def get_reqs(req_file):
    with open(os.path.join(_PROJECT_ROOT, req_file), 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]


setup(
    name="ai_puti",
    version="0.1.0b14",
    description="puti: MultiAgent-based package for LLM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="llm, multiagent, package, agent, twikit, openai, websearch, terminal, python, file, fastapi, mcp",
    maintainer="obstaclews",
    author="obstaclews",
    author_email="obstaclesws@qq.com",
    url="https://github.com/aivoyager/puti",
    packages=find_packages(exclude=["test*", "data", "docs", "api*"]),
    package_data={
        'puti': ['conf/config.yaml', 'py.typed'],
    },
    include_package_data=True,
    install_requires=get_reqs('requirements.txt'),
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'puti = puti.cli:main',
            'puti-setup = puti.bootstrap:main',
        ],
    },
)
