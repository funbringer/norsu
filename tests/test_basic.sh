set -v

export NORSU_PATH="$PWD/pg"

# install instance
norsu install master --extensions auto_explain

# show configure flags
"$(norsu path master)/bin/pg_config" > /dev/null

# run a query
echo show max_connections | norsu run master \
	--psql --config <(echo max_connections = 25) \
	-- -Xatq 2> /dev/null

# remove only installation
rm -rf "$(norsu path master)"

# quick reinstall
norsu install master

# remove instance
norsu remove master

# remove dir
rm -rf "$NORSU_PATH"
