from setuptools import setup


setup(
    name='copywriter',
    tests_require=['pytest'],
    python_requires='>=3.6',
    py_modules=['copywriter'],
    entry_points={
        'console_scripts': ['copywriter=copywriter:main'],
    }
)
