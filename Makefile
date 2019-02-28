install:
	install ebase.py /usr/local/bin/ebase
	rm -rf /usr/local/bin/ebase_config
	cp -r ebase_config /usr/local/bin/ebase_config

uninstall:
	rm -f /usr/local/bin/ebase
	rm -rf /usr/local/bin/ebase_config
