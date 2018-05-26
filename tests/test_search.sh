set -v

export NORSU_PATH=$PWD/pg

# search for an old release
norsu search 9.2

# remove dir
rm -rf $NORSU_PATH
