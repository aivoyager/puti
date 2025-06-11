from setuptools import setup, find_packages
import os

with open(os.path.join(os.path.dirname(__file__), "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai_puti",
    version="0.1.0b7",
    description="puti: MultiAgent-based package for LLM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="llm, multiagent, package, agent, twikit, openai, websearch, terminal, python, file, fastapi, mcp",
    maintainer="obstaclews",
    author="obstaclews",
    author_email="obstaclesws@qq.com",
    url="https://github.com/aivoyager/puti",
    packages=find_packages(exclude=["test*", "celery_queue*", "data", "docs", "api*"]),
    include_package_data=True,
    install_requires=[
        "wheel==0.45.1",
        "ollama==0.5.1",
        "click==8.2.1",
        "pytest==8.4.0",
        "googlesearch-python==1.3.0",
        "numpy==2.2.6",
        "scikit-learn==1.7.0",
        "tiktoken==0.9.0",
        "openai==1.84.0",
        "mcp==1.9.3",
        "anthropic==0.52.2",
        "python-box==7.3.2",
        "pyyaml==6.0.2",
        "faiss-cpu==1.11.0",
        "pandas==2.3.0",
        "jinja2==3.1.6",
        "twikit==2.3.3",
        "pytest-asyncio==1.0.0",
        "pydantic==2.10.6",
        "questionary==2.0.1",
        "rich==13.7.1",
        "python-dotenv==1.0.1",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'puti = puti.cli:main',
        ],
    },
)
