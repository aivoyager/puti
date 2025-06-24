from setuptools import setup, find_packages
import os

with open(os.path.join(os.path.dirname(__file__), "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai_puti",
    version="0.1.0b11",
    description="puti: MultiAgent-based package for LLM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="llm, multiagent, package, agent, twikit, openai, websearch, terminal, python, file, fastapi, mcp",
    maintainer="obstaclews",
    author="obstaclews",
    author_email="obstaclesws@qq.com",
    url="https://github.com/aivoyager/puti",
    packages=find_packages(exclude=["test*", "celery_queue*", "data", "docs", "api*"]),
    package_data={
        'puti': ['conf/config.yaml'],
    },
    include_package_data=True,
    install_requires=[
        "wheel>=0.40.0",
        "ollama>=0.4.0",
        "click>=8.1.3",
        "pytest>=8.0.0",
        "googlesearch-python>=1.1.0",
        "scikit-learn>=1.3.0",
        "tiktoken>=0.5.0",
        "openai>=1.10.0",
        "mcp>=1.8.0",
        "anthropic>=0.18.0",
        "python-box>=7.1.0",
        "pyyaml>=6.0.0",
        "faiss-cpu>=1.7.4",
        "pandas>=2.0.0",
        "jinja2>=3.1.0",
        "twikit>=2.0.0",
        "pytest-asyncio>=0.21.0",
        "pydantic>=2.5.0",
        "questionary>=2.0.0",
        "rich>=13.0.0",
        "python-dotenv>=1.0.0",
        "numpy>=2.0.0",
        "numexpr>=2.8.0",
        "celery>=5.3.0",
        "tenacity>=8.2.0",
        "croniter>=2.0.0"
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
            'puti-setup = puti.bootstrap:main',
        ],
    },
)
