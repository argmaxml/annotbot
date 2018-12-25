from distutils.core import setup

setup(
    name='Annotbot',
    py_modules=["client.py"],
    requires=["pandas"],
    version='0.11',
    python_requires='>=3.4',
    description='Annotbot.com client',
    author='Uri Goren',
    author_email='uri@goren4u.com',
    url='https://github.com/urigoren/Annotbot',
    download_url='https://github.com/urigoren/Annotbot/archive/master.zip',
    keywords=['natural-language-processing', 'computer-vision', 'supervised-learning'],
    classifiers=[],
)
