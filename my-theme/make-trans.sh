#!/bin/sh
pybabel extract --mapping babel.cfg --output messages.pot ./
# pybabel init --input-file messages.pot --output-dir translations/ --locale lang --domain messages
pybabel update --input-file messages.pot --output-dir translations/ --domain messages
pybabel compile --directory translations/ --domain messages
