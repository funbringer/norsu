set -v

export NORSU_PATH="$PWD/pg"

# pull master
norsu pull master

# check that dir exists
if [ -e "$NORSU_PATH/.norsu/master" ]; then echo OK; fi

# purge master
norsu purge master

# check that dir has been removed
if [ ! -e "$NORSU_PATH/.norsu/master" ]; then echo OK; fi

# remove dir
rm -rf "$NORSU_PATH"
