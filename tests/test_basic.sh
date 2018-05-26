set -v

export NORSU_PATH=$PWD/pg

# install instance
norsu install master

# show configure flags
$(norsu path master)/bin/pg_config > /dev/null

# useless purge
norsu purge master

# remove instance
norsu remove master

# remove dir
rm -rf $NORSU_PATH
