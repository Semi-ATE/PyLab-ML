.. rule documentation master file

.. image:: _static/tips.jpg 

Last change: |today|

All contributors are welcome, but please adhere to the following rules :
   
Rules, Tips and Tricks 
======================
Here you will find rules, but also tips and tricks on how to create the documentation and how you should configure Spyder.

The documentation itself is based on `Sphinx <https://www.sphinx-doc.org/en/master/>`_  and the doc-strings inside the source code.
For Sphinx use `reStructuredText <https://devguide.python.org/documenting/>`_ as its markup language.
This `quickreference <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_ can help you for beginning. 

this documentation is automatically generated as soon as a push is executed in github. If you want to generate it by hand:

   >>> conda activate 'your environment'
   >>> mamba install sphinx sphinx-rtd-theme myst-parser sphinx-markdown-tables
   >>> cd docs
   >>> ./make clean
   >>> ./make html
   
   all import modules have to be in the sys.path from the file conf.py .
   Otherwise you get a WARNING like :

   * WARNING: [autosummary] failed to import 'instruments.attributes': no module named instruments.attributes
                                         
   and the module doesn't compile. 


Spyder Preferences
------------------
For the python code themselves, we use PEP8 as an uniform code styling. 
In the Spyder Framework, you have to enable the code style linting (the images show Spyder V4.0.x preferences):

.. image:: _static/Spyder_enable_codestyle.png
   :width: 400
   :class: hover150
   :alt:   Spyder_enable_codestyle


and you have to enable the docstring style linting

.. image:: _static/Spyder_enable_docstyle.png
   :width: 400
   :class: hover150
   :alt:   Spyder_enable_docstyle
   


If you think all the code styling is too much work and you don't have time to learn it, then you can also use the `Black <https://github.com/psf/black>`_ program.
For installing, open  Maxiconda Powershell, go to your current TCC workarea and write:

   >>> mamba install black
   >>> cd /instruments/your_path/....
   >>> black your_file.py
   
   look on the code now(attention, the file is overwritten), it's now PEP8 style. However, the docstrings are not processed. You have to do it yourself.....
	  

Rules for writing Tests
-----------------------	  
1. For file- and directory name use only lower case. Windows does not handle capitalized files correctly. In linux is 'test.py' and 'Test.py' two different file, but not in windows! 
2. Use short function name. E.q. 'off()' and not 'dmm_switch_off()' 
3. Code is your enemy.
4. Avoid copy and paste.
5. IF you write new functions or libraries: Someone in the world may have already solved the same problem. Google is your friend!
   For libraries start your search e.q. at https://pypi.org/ and https://anaconda.org/


