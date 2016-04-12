find . -name "*.so" -exec rm -v {} \;
find . -name "*.pyc" -exec rm -v {} \;
rm -rvf build dist
rm -rvf acispy.egg-info
