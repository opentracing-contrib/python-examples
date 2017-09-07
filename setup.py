from setuptools import setup

setup(
    name='python-examples',
    version='0.0.1.dev0',
    author='The OpenTracing Authors',
    author_email='info@opentracing.io',
    license='Apache License 2.0',
    url='https://github.com/opentracing-contrib/python-examples',
    keywords=['python', 'opentracing'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache License 2.0',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development',
    ],
    packages=['tests'],
    platforms='any',
    install_requires=[
        'opentracing>=1.2.1,<1.3',
        'basictracer>=2.2,<2.3',
        'six>=1.10.0,<2.0',
        'futures',
        'tornado',
        'gevent',
    ],
    extras_require={
        'tests': [
            'flake8<3',  # https://github.com/zheller/flake8-quotes/issues/29
            'flake8-quotes',
            'pytest>=2.7,<3',
        ]
    },
)
