export DB_TYPE=mysql

export MYSQL_HOST=localhost
export MYSQL_PORT=3307
export MYSQL_DB=galileo
export MYSQL_USER=galileo
export MYSQL_PASSWORD=galileo

exec python -m galileo.cli.experimentd "$@"
