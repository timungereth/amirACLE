from setuptools import setup, find_packages

setup(
    name="button_menu_app",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'PyQt5>=5.15.0',
        'pywin32>=228',
        'keyboard>=0.13.5',
        'pynput>=1.7.0',
    ],
    entry_points={
        'gui_scripts': [
            'button-menu=button_menu_app.button_menu:main',
        ],
    },
    author="Your Name",
    description="A floating scroll control application",
    python_requires=">=3.6",
)