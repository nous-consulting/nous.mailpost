from setuptools import setup, find_packages

setup(
    name='nous.mailpost',
    version='0.5.2',
    description='Email processor that posts the email received to a url',
    author='Ignas Mikalajunas',
    author_email='ignas@nous.lt',
    url='http://github.com/Ignas/nous.mailpost/',
    classifiers=["Development Status :: 3 - Alpha",
                 "Environment :: Web Environment",
                 "Topic :: Communications :: Email",
                 "Intended Audience :: Developers",
                 "License :: OSI Approved :: GNU General Public License (GPL)",
                 "Programming Language :: Python"],
    install_requires=[
        'mox',
        'zope.testing'
    ],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    zip_safe=True,
    license="GPL",
    entry_points="""
    [console_scripts]
    mailpost = nous.mailpost:main
    """,
)
